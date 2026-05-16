#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : cmds.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 28.10.2024
# (c) Camille Scott, 2024

from argparse import Namespace
from pathlib import Path
import shutil

from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich.console import Console

from .args import ArgParser, arggroup, commands, common_args, EnumAction
from .chat import summarize_page
from .config import AppConfig
from .models import NoteSummary, PageCategory, summary_schema_from_category
from .note import WebNote
from . import service as service_mod


def _resolve_model(args: Namespace, cfg: AppConfig, console: Console) -> str | None:
    requested = args.model or cfg.openai.default_model
    if requested not in cfg.openai.models:
        console.print(
            f'[red]Model {requested!r} is not in configured models: '
            f'{cfg.openai.models}[/red]'
        )
        return None
    return requested


def _resolve_reasoning(args: Namespace, cfg: AppConfig) -> str:
    return args.reasoning or cfg.openai.default_reasoning


@common_args.postprocessor()
def resolve_config(args: Namespace):
    console = Console(stderr=True)
    try:
        cfg = AppConfig.load(args.config)
    except (FileNotFoundError, ValueError) as e:
        console.print(f'[red]{e}[/red]')
        raise

    args.model = _resolve_model(args, cfg, console)
    if args.model is None:
        raise ValueError('No model specified')

    args.reasoning = _resolve_reasoning(args, cfg)
    args.cfg = cfg

    load_dotenv()


@arggroup('Category')
def category_args(parser: ArgParser):
    parser.add_argument('--category', '-c', type=PageCategory, action=EnumAction)


@category_args.apply()
@commands.register('process', 'note',
                   help='Process a note with the LLM and rewrite it.')
async def process_note(args: Namespace):
    console = Console(stderr=True)


    console.log(f'Load {args.note}...')
    note = WebNote(args.note)

    if note.cryptic_processed and not args.force:
        console.log('[red] Note already processed and not --force, exiting.')
        return 1

    if args.category:
        schema = summary_schema_from_category(args.category)
        console.log(f'[yellow] Forcing {schema} as Schema')
    else:
        schema = NoteSummary

    client = AsyncOpenAI()
    try:
        with console.status(f'[bold blue]Wait for OpenAI response...'):
            summary, completion = await summarize_page(
                client,
                note.content,
                model=args.model,
                system_prompt=args.cfg.prompt.text,
                reasoning=args.reasoning,
                schema=schema,
            )
    finally:
        await client.close()

    if summary is None:
        console.print(f'[red] Error processing note!')
        return 1

    console.log(f'Processed note using {completion.usage.total_tokens} tokens.')
    console.print(summary)

    if args.backup:
        console.log('Backup note...')
        shutil.copy(args.note, args.note.with_suffix('.bak'))

    console.log('Update and save note...')
    note.process_summary(summary)
    note.save()

    console.rule('Processed Note')
    note.to_console(console)

    return 0


@process_note.args()
def _(parser: ArgParser):
    parser.add_argument('--note', '-i', type=Path, required=True)
    parser.add_argument('--force', '-f', default=False, action='store_true')
    parser.add_argument('--backup', '-b', default=False, action='store_true')


@commands.register('service',
                   help='Watch configured vault directories and process new notes.')
async def service_cmd(args: Namespace):
    console = Console(stderr=True)

    svc = args.cfg.require_service()
    if args.max_concurrent is not None:
        svc.max_concurrent = args.max_concurrent

    return await service_mod.run(
        console=console,
        cfg=args.cfg,
        svc=svc,
        model=args.model,
        reasoning=args.reasoning,
        once=args.once,
    )


@service_cmd.args()
def _(parser: ArgParser):
    parser.add_argument('--max-concurrent', type=int, default=None,
                        help='Override service.max_concurrent from config.')
    parser.add_argument('--once', default=False, action='store_true',
                        help='Drain existing files and exit instead of watching.')
