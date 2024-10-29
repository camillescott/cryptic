#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : __main__.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 29.10.2024
# (c) Camille Scott, 2024


import sys

from .cmds import commands

def main():
    return commands.run()


if __name__ == '__main__':
    sys.exit(main())
