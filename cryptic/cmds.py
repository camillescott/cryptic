#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : cmds.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 28.10.2024
# (c) Camille Scott, 2024

from argparse import Namespace
from pathlib import Path

from rich.console import Console

from .args import ArgParser, arggroup, commands, EnumAction
from .chat import summarize_page
from .models import NoteSummary, PageCategory, summary_schema_from_category
from .note import WebNote


@arggroup('Category')
def category_args(parser: ArgParser):
    parser.add_argument('--category', '-c', type=PageCategory, action=EnumAction)


@category_args.apply()
@commands.register('process', 'note',
                   help='Process a note with the LLM and rewrite it.')
def process_note(args: Namespace):
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

    with console.status(f'[bold blue]Wait for OpenAI response...') as status:
        summary, completion = summarize_page(note.content, schema=schema)
        if summary is None:
            console.print(f'[red] Error processing note!')
            return 1

    console.log(f'Processed note using {completion.usage.total_tokens} tokens.')
    console.print(summary)

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

