#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : cmds.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 28.10.2024
# (c) Camille Scott, 2024

from argparse import Action, ArgumentParser, _SubParsersAction, Namespace
from collections import deque
from enum import Enum
from itertools import pairwise
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec

from rich.console import Console

from .chat import summarize_page
from .models import NoteSummary, PageCategory, summary_schema_from_category
from .note import WebNote


P = ParamSpec('P')
NamespaceFunc = Callable[Concatenate[Namespace, P], int | None]


class EnumAction(Action):

    def __init__(self, **kwargs):
        # Pop off the type value
        enum = kwargs.pop("type", None)

        # Ensure an Enum subclass is provided
        if enum is None:
            raise ValueError("type must be assigned an Enum when using EnumAction")
        if not issubclass(enum, Enum):
            raise TypeError("type must be an Enum when using EnumAction")

        # Generate choices from the Enum
        kwargs.setdefault("choices", tuple(e.name for e in enum))

        super(EnumAction, self).__init__(**kwargs)

        self._enum = enum

    def __call__(self, parser, namespace, values, option_string=None):
        # Convert value back into an Enum
        enum = self._enum[values]
        setattr(namespace, self.dest, enum)


class SubcmdHelper:

    def __init__(self, parser: ArgumentParser):
        self.parser = parser

    def args(self, arg_adder: Callable[[ArgumentParser], Action | None]):
        arg_adder(self.parser)
        return arg_adder

    def func(self):
        return self.parser._defaults['func']


class CmdTree:

    def __init__(self, root: ArgumentParser | None = None, **kwargs):

        if root is None:
            self.root = ArgumentParser(**kwargs)
        else:
            self.root = root
        self.root.set_defaults(func = lambda _: self.root.print_help())
        if not self._get_subparsers(self.root):
            self.root.add_subparsers()

    def parse_args(self):
        return self.root.parse_args()

    def run(self):
        args = self.parse_args()
        args.func(args)

    def _get_subparser_action(self, parser: ArgumentParser) -> _SubParsersAction | None:
        for action in parser._actions:
            if isinstance(action, _SubParsersAction):
                return action
        return None

    def _get_subparsers(self, parser: ArgumentParser):
        action = self._get_subparser_action(parser)
        if action is not None:
            yield from action.choices.items()


    def _find_cmd(self, cmd_name: str, root: ArgumentParser | None = None) -> ArgumentParser | None:
        if root is None:
            root = self.root
        
        subparser_deque = deque(self._get_subparsers(root))

        while subparser_deque:
            root_name, root_parser = subparser_deque.popleft()
            if root_name == cmd_name:
                return root_parser
            else:
                subparser_deque.extend(self._get_subparsers(root_parser))

        return None

    def _find_cmd_chain(self, cmd_fullname: list[str]):
        root_name, leaf_name = cmd_fullname[0], cmd_fullname[-1]
        if (root_parser := self._find_cmd(root_name)) is None:
            return [None] * len(cmd_fullname)
        elif len(cmd_fullname) == 1:
            return [root_parser]
        else:
            chain : list[ArgumentParser | None] = [root_parser]
            for next_name in cmd_fullname[1:]:
                found = False
                for child_name, child_parser in self._get_subparsers(root_parser):
                    if child_name == next_name:
                        root_parser = child_parser
                        chain.append(child_parser)
                        found = True
                        break
                if not found:
                    break
            if len(chain) != len(cmd_fullname):
                chain.extend([None] * (len(cmd_fullname) - len(chain)))
            return chain

    def _add_child(self, root: ArgumentParser,
                         child_name: str,
                         func = None,
                         aliases: list[str] | None = None,
                         help: str | None = None):
        if (subaction := self._get_subparser_action(root)) is None:
            subaction = root.add_subparsers()
        child = subaction.add_parser(child_name, help=help, aliases=aliases if aliases else [])
        cmd_func = (lambda _: child.print_help()) if func is None else func
        child.set_defaults(func=cmd_func)
        return child

    def register_cmd(self, cmd_fullname: list[str],
                           cmd_func: NamespaceFunc[P],
                           aliases: list[str] | None = None,
                           help: str | None = None):

        chain = self._find_cmd_chain(cmd_fullname)
        if not any(map(lambda el: el is None, chain)):
            raise ValueError(f'subcommand {cmd_fullname} already registered')
        if chain[0] is None:
            chain = [self.root] + chain
            cmd_fullname = [self.root.prog] + cmd_fullname
        leaf_name = cmd_fullname[-1]
        for i, j in pairwise(range(len(chain))):
            if chain[j] is None:
                if cmd_fullname[j] == leaf_name:
                    return self._add_child(chain[i], leaf_name, func=cmd_func, aliases=aliases, help=help)
                else:
                    child = self._add_child(chain[i], cmd_fullname[j])
                    chain[j] = child
        raise ValueError(f'{leaf_name} was not registered')


    def register(self, cmd_fullname: list[str],
                       aliases: list[str] | None = None,
                       help: str | None = None):

        def wrapper(cmd_func: NamespaceFunc[P]):
            return SubcmdHelper(self.register_cmd(cmd_fullname,
                                                  cmd_func,
                                                  aliases=aliases,
                                                  help=help))

        return wrapper


commands = CmdTree()


@commands.register(['process', 'note'],
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
    

@process_note.args
def _(parser: ArgumentParser):
    parser.add_argument('--note', '-i', type=Path, required=True)
    parser.add_argument('--force', '-f', default=False, action='store_true')


@process_note.args
def category_arg(parser: ArgumentParser):
    parser.add_argument('--category', '-c', type=PageCategory, action=EnumAction)
