#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : args.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 31.10.2024
# (c) Camille Scott, 2024

from argparse import Action, ArgumentParser, _ArgumentGroup, _SubParsersAction, Namespace
from collections import deque
from enum import Enum
from functools import wraps
from itertools import pairwise
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec, Union

from rich.console import Console

from .chat import summarize_page
from .models import NoteSummary, PageCategory, summary_schema_from_category
from .note import WebNote


P = ParamSpec('P')
Subparsers = _SubParsersAction
NS = Namespace
NamespaceFunc = Callable[Concatenate[NS, P], Union[int, None]]
SubCommandFunc = Callable[Concatenate[Subparsers, P], None]
ArgParser = ArgumentParser | _ArgumentGroup
ArgAdderFunc = Callable[[ArgParser], Action | None]


class SubCmd:

    def __init__(self, parser: ArgumentParser,
                       name: str,
                       cmd_tree: 'CmdTree'):
        self.parser = parser
        self.name = name
        self.cmd_tree = cmd_tree

    def args(self, groupname: str | None = None,
                   desc: str | None = None,
                   common: bool = False):
        
        def wrapper(arg_adder: ArgAdderFunc):
            group = ArgGroup(groupname, arg_adder, desc=desc)
            apply_func = group.apply(common=common)
            apply_func(self)
            return group

        return wrapper

    @property
    def func(self):
        return self.parser._defaults['func']

    @func.setter
    def func(self, new_func: Callable[[Namespace], None]):
        self.parser._defaults['func'] = new_func


class CmdTree:

    def __init__(self, root: ArgumentParser | None = None, **kwargs):
        '''Manages a tree of argparse subparsers and provides
        decorators for registering functions on those subparsers.

        Args:
            root: The root parser.
        '''

        if root is None:
            self._root = ArgumentParser(**kwargs)
        else:
            self._root = root
        self._root.set_defaults(func = lambda _: self.print_help())
        if not self._get_subparsers(self._root):
            self._root.add_subparsers()
        
        self.root = SubCmd(self._root,
                           self._root.prog,
                           self)
        self.common_adders: list[tuple[str | None, ArgAdderFunc]] = []

    def parse_args(self, *args, **kwargs):
        return self._root.parse_args(*args, **kwargs)

    def run(self, args: Namespace | None = None):
        '''Parse args and execute the registered functions.
        '''
        if args is None:
            args = self.parse_args()
        return args.func(args)

    def _get_subparser_action(self, parser: ArgumentParser) -> _SubParsersAction | None:
        '''Extraction the subparser Action from the given parser.

        Args:
            parser: parser to search.

        Returns:
            The subparser Action or None
        '''
        for action in parser._actions:
            if isinstance(action, _SubParsersAction):
                return action
        return None

    def _get_subparsers(self, parser: ArgumentParser):
        '''Search if the given parser has subparsers registered on it.

        Args:
            parser: Parser to search.

        Returns:
            Discovered subparsers or None
        '''
        action = self._get_subparser_action(parser)
        if action is not None:
            yield from action.choices.items()

    def _find_cmd(self, cmd_name: str,
                        root: ArgumentParser | None = None) -> ArgumentParser | None:
        '''Find the first instance of a subcommand of the given name,
        breadth-first, starting at the given root parser if provided.

        Args:
            cmd_name: subcommand name to search for
            root: the parser to search from, or the registered root

        Returns:
            The parser associated with the given name
        '''
        if root is None:
            root = self._root
        
        if cmd_name == root.prog:
            return root

        subparser_deque = deque(self._get_subparsers(root))

        while subparser_deque:
            root_name, root_parser = subparser_deque.popleft()
            if root_name == cmd_name:
                return root_parser
            else:
                subparser_deque.extend(self._get_subparsers(root_parser))

        return None

    def gather_subtree(self, root_name: str | None) -> list[ArgumentParser]:
        if root_name is None:
            root = self._root
        else:
            root = self._find_cmd(root_name)
        if root is None:
            return []
        found : list[ArgumentParser] = [root]
        parser_q = deque(self._get_subparsers(root))
        while parser_q:
            _, root = parser_q.popleft()
            parser_q.extend(self._get_subparsers(root))
            found.append(root)

        return found

    def _find_cmd_chain(self, cmd_fullname: list[str]) -> list[ArgumentParser | None]:
        root_name =  cmd_fullname[0]
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
            chain = [self._root] + chain
            cmd_fullname = [self._root.prog] + cmd_fullname
        leaf_name = cmd_fullname[-1]

        for i, j in pairwise(range(len(chain))):
            if chain[j] is None:
                if chain[i] is None:
                    raise ValueError(f'Bad argument chain: {chain[i]}->{chain[j]}')
                elif cmd_fullname[j] == leaf_name:
                    return self._add_child(chain[i], leaf_name, func=cmd_func, aliases=aliases, help=help)
                else:
                    child = self._add_child(chain[i], cmd_fullname[j])
                    chain[j] = child

        raise ValueError(f'{leaf_name} was not registered')


    def register(self, *cmd_fullname: str,
                       aliases: list[str] | None = None,
                       help: str | None = None):

        def wrapper(cmd_func: NamespaceFunc[P]):
            return SubCmd(self.register_cmd(list(cmd_fullname),
                                            cmd_func,
                                            aliases=aliases,
                                            help=help),
                                cmd_fullname[-1],
                                self)

        return wrapper

    def register_common_args(self, cmd_root: str | None,
                                   arg_adder: ArgAdderFunc):
        self.common_adders.append((cmd_root, arg_adder))

    def _apply_common_args(self):
        '''Apply the registered common argument adders to their parsers.

        Yes, this repeatedly traverses the parser tree a bunch of times
        and could be optimized. If your command tree is big enough that
        this matters you are probably doing something deranged.
        '''
        for root_name, arg_adder in self.common_adders:
            for parser in self.gather_subtree(root_name):
                arg_adder(parser)

    def _get_help(self, parser,
                          cmds: list[str],
                          name: str | None = None,
                          level: int = 0):
        indent = '  ' * level
        if name is None:
            name = parser.prog
        args = []
        for action in parser._actions:
            if isinstance(action, _SubParsersAction):
                for subparser_action, (subparser_name, subparser) in zip(action._get_subactions(), action.choices.items()):
                    help = subparser_action.help or ''
                    cmds.append(f'{indent}  {subparser_action.dest}: {help}')
                    self._get_help(subparser, cmds, name=subparser_name, level=level+1)  # Recursively traverse subparsers
            else:
                args.append(action.dest)

    def print_help(self):
        cmds = [self._root.format_usage(),
                'Subcommands:']
        self._get_help(self._root, cmds, self._root.prog)
        print('\n'.join(cmds))



def postprocess_args(func: Callable[[Namespace], None],
                     postprocessors: list[Callable[[Namespace], None]]):

    @wraps(func)
    def wrapper(args: Namespace):
        for postproc_func in postprocessors:
            postproc_func(args)
        func(args)

    return wrapper


class ArgGroup:

    def __init__(self, group_name: str | None,
                       arg_func: ArgAdderFunc,
                       desc: str | None = None):
        self.group_name = group_name
        self.arg_func = arg_func
        self.desc = desc
        self.postprocessors: list[Callable[[Namespace], None]] = []

    def apply(self, common: bool = False, *args, **kwargs):

        def _apply_group(parser: ArgumentParser):
            if self.group_name is None:
                group = parser
            else:
                group = parser.add_argument_group(title=self.group_name,
                                                  description=self.desc)
            self.arg_func(group, *args, **kwargs)
            parser.set_defaults(func=postprocess_args(parser.get_default('func'),
                                                      self.postprocessors))

        def wrapper(target: SubCmd):
            if common:
                target.cmd_tree.register_common_args(target.name, _apply_group)
            else:
                _apply_group(target.parser)
            return target

        return wrapper

    def postprocessor(self, func: Callable[[Namespace], None]):
        self.postprocessors.append(func)
        return func


def arggroup(groupname: str,
             desc: str | None = None):
    def wrapper(adder_func: ArgAdderFunc):
        return ArgGroup(groupname, adder_func, desc=desc)
    return wrapper


class EnumAction(Action):
    """
    Argparse action for handling Enums
    """
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


commands = CmdTree()

