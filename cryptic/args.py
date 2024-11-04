#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : args.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 31.10.2024
# (c) Camille Scott, 2024

from argparse import Action
from enum import Enum

from ponderosa import CmdTree, ArgParser, arggroup


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
