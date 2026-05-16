#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : service.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>

from __future__ import annotations

import asyncio
import signal
import shutil
import traceback
from pathlib import Path

from asyncinotify import Inotify, Mask
from openai import AsyncOpenAI
from rich.console import Console

from .chat import summarize_page
from .config import AppConfig, ServiceCfg, VaultCfg
from .note import WebNote, normalize_tag


QueueItem = tuple[Path, VaultCfg]


async def _process_one(
    client: AsyncOpenAI,
    cfg: AppConfig,
    svc: ServiceCfg,
    vault: VaultCfg,
    model: str,
    reasoning: str,
    path: Path,
    in_flight: set[str],
    console: Console,
) -> None:
    tag = f'\\[{vault.name}] {path.name}'
    pkey = str(path)
    if pkey in in_flight:
        console.log(f'[dim]already in flight {tag}; skipping duplicate event[/dim]')
        return
    if not path.exists():
        console.log(f'[dim]vanished before pickup {tag}; skipping[/dim]')
        return
    in_flight.add(pkey)
    if svc.pickup_delay_seconds > 0:
        console.log(
            f'[dim]pickup {tag} '
            f'(settling for {svc.pickup_delay_seconds}s)[/dim]'
        )
    else:
        console.log(f'[dim]pickup {tag}[/dim]')

    try:
        if svc.pickup_delay_seconds > 0:
            await asyncio.sleep(svc.pickup_delay_seconds)
            if not path.exists():
                console.log(f'[dim]vanished during settle {tag}; skipping[/dim]')
                return

        try:
            note = WebNote(path)
        except Exception as e:
            console.print(f'[red]load failed {tag}: {e}[/red]')
            return

        if note.cryptic_processed:
            console.log(
                f'[yellow]cryptic_processed=true on {tag}; '
                f'leaving in input_dir for manual review[/yellow]'
            )
            return

        prev_tries = note.cryptic_tries or 0
        if prev_tries >= svc.max_tries:
            console.log(
                f'[yellow]skip[/yellow] {tag} '
                f'(cryptic_tries={prev_tries} >= max_tries={svc.max_tries})'
            )
            return

        archive_path = vault.originals_dir / path.name
        try:
            shutil.copy2(str(path), str(archive_path))
        except Exception as e:
            console.print(f'[red]archive to originals_dir failed for {tag}: {e}[/red]')
            console.print(traceback.format_exc())
            return

        note.cryptic_tries = prev_tries + 1
        try:
            note.save()
        except Exception as e:
            console.print(f'[red]could not record cryptic_tries on {tag}: {e}[/red]')
            return

        console.log(
            f'[blue]processing[/blue] {tag} '
            f'(try {note.cryptic_tries}/{svc.max_tries})'
        )
        try:
            summary, completion = await summarize_page(
                client,
                note.content,
                model=model,
                system_prompt=cfg.prompt.text,
                reasoning=reasoning,
            )
            if summary is None:
                raise RuntimeError('OpenAI returned no parsed summary')
        except Exception as e:
            console.print(f'[red]failed {tag}: {e}[/red]')
            console.print(traceback.format_exc())
            return

        try:
            note.process_summary(summary)
            kebab = normalize_tag(summary.metadata.title)
            dest_name = f'{kebab}.md' if kebab else path.name
            dest = vault.output_dir / dest_name
            note.save(dest)
            path.unlink()
            console.log(
                f'[green]done[/green] {tag} -> {dest_name} '
                f'({completion.usage.total_tokens} tokens, '
                f'original={archive_path.name})'
            )
        except Exception as e:
            console.print(f'[red]post-process write failed for {tag}: {e}[/red]')
            console.print(traceback.format_exc())
    except Exception as e:
        console.print(f'[red]unexpected error on {tag}: {e}[/red]')
        console.print(traceback.format_exc())
    finally:
        in_flight.discard(pkey)


async def _worker(
    name: str,
    queue: asyncio.Queue[QueueItem],
    sem: asyncio.Semaphore,
    client: AsyncOpenAI,
    cfg: AppConfig,
    svc: ServiceCfg,
    model: str,
    reasoning: str,
    in_flight: set[str],
    console: Console,
) -> None:
    while True:
        path, vault = await queue.get()
        try:
            async with sem:
                await _process_one(
                    client, cfg, svc, vault, model, reasoning, path, in_flight, console
                )
        except asyncio.CancelledError:
            queue.task_done()
            raise
        except Exception as e:
            console.print(f'[red]worker {name} caught unhandled: {e}[/red]')
            console.print(traceback.format_exc())
            queue.task_done()
        else:
            queue.task_done()


async def _watcher(
    inotify: Inotify,
    vault_by_dir: dict[Path, VaultCfg],
    queue: asyncio.Queue[QueueItem],
) -> None:
    async for event in inotify:
        watch = event.watch
        if watch is None or event.name is None:
            continue
        vault = vault_by_dir.get(watch.path)
        if vault is None:
            continue
        path = vault.input_dir / event.name
        if path.suffix != '.md':
            continue
        await queue.put((path, vault))


async def run(
    *,
    console: Console,
    cfg: AppConfig,
    svc: ServiceCfg,
    model: str,
    reasoning: str,
    once: bool,
) -> int:
    for name, vault in svc.vaults.items():
        if not vault.input_dir.is_dir():
            console.print(
                f'[red]vault {name!r}: input_dir does not exist: {vault.input_dir}[/red]'
            )
            return 1
        vault.output_dir.mkdir(parents=True, exist_ok=True)
        vault.originals_dir.mkdir(parents=True, exist_ok=True)

    queue: asyncio.Queue[QueueItem] = asyncio.Queue()
    sem = asyncio.Semaphore(svc.max_concurrent)
    in_flight: set[str] = set()

    for vault in svc.vaults.values():
        for p in sorted(vault.input_dir.glob('*.md')):
            queue.put_nowait((p, vault))
    console.log(
        f'[bold]service[/bold] vaults={list(svc.vaults)} '
        f'max_concurrent={svc.max_concurrent} max_tries={svc.max_tries} '
        f'pickup_delay={svc.pickup_delay_seconds}s '
        f'model={model} reasoning={reasoning} seeded={queue.qsize()}'
    )

    client = AsyncOpenAI()
    workers: list[asyncio.Task] = []
    for i in range(svc.max_concurrent):
        t = asyncio.create_task(
            _worker(
                f'w{i}', queue, sem, client, cfg, svc, model, reasoning,
                in_flight, console,
            ),
            name=f'cryptic-worker-{i}',
        )
        workers.append(t)

    try:
        if once:
            await queue.join()
            return 0

        with Inotify() as inotify:
            vault_by_dir = {v.input_dir: v for v in svc.vaults.values()}
            for vault in svc.vaults.values():
                inotify.add_watch(vault.input_dir, Mask.CLOSE_WRITE | Mask.MOVED_TO)

            cancel_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, cancel_event.set)

            watcher_task = asyncio.create_task(
                _watcher(inotify, vault_by_dir, queue),
                name='cryptic-watcher',
            )

            await cancel_event.wait()
            console.log('[yellow]shutdown requested; draining…[/yellow]')

            watcher_task.cancel()
            try:
                await watcher_task
            except (asyncio.CancelledError, Exception):
                pass

            await queue.join()
            return 0
    finally:
        for t in workers:
            t.cancel()
        for t in workers:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        await client.close()
