#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : markdown.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2024


from functools import singledispatch
import textwrap
from typing import Any

from .models import (NoteInfo,
                     PaperInfo,
                     ArticleInfo,
                     EventInfo,
                     ProductInfo,
                     DiscussionInfo,
                     MediaInfo,
                     SoftwareInfo,
                     ReferenceInfo)


def md_escape(text: str) -> str:
    special_characters = [
        ('\\', '\\\\'),  
        ('`', '\\`'),
        ('*', '\\*'),
        ('_', '\\_'),
        ('{', '\\{'),
        ('}', '\\}'),
        ('[', '\\['),
        (']', '\\]'),
        ('(', '\\('),
        (')', '\\)'),
        ('>', '\\>'),
        ('#', '\\#'),
        ('+', '\\+'),
        ('-', '\\-'),
        ('.', '\\.'),
        ('!', '\\!')
    ]

    for char, escape in special_characters:
        text = text.replace(char, escape)

    return text


def md_bullets(source: list[Any], symbol: str = '-'):
    for item in source:
        yield symbol, item


def md_enumerate(source: list[Any]):
    for i, item in enumerate(source):
        yield f'{i}.', item


def md_bold(text: str):
    return f'**{text}**'


def md_italic(text: str):
    return f'_{text}_'


def md_list(items: list[Any], numbered: bool = False):
    markers = md_enumerate if numbered else md_bullets

    result = []
    for marker, item in markers(items):
        result.append(f'{marker} {item}')

    return '\n'.join(result)


def md_header(item: str, depth: int = 2):
    return f'{"#" * depth} {item}'


def md_link(url: str, text: str | None = None):
    if text is None:
        text = url
    return f'[{text}]({url})'


@singledispatch
def noteinfo_to_md(info: NoteInfo) -> str:
    elements : list[str] = [info.summary]
    return '\n\n'.join(elements)


@noteinfo_to_md.register
def _(info: PaperInfo) -> str:
    elements : list[str] = [info.summary]
    elements.append(md_header('Abstract', depth=2))
    elements.append(info.abstract)
    elements.append(md_header('Foudational Work', depth=2))
    elements.append(info.foundations)
    elements.append(md_header('Takeaways', depth=2))
    elements.append(md_list(info.takeaways))
    return '\n\n'.join(elements)


@noteinfo_to_md.register
def _(info: ArticleInfo):
    elements : list[str] = [info.summary]
    elements.append(md_header('Foudational Work', depth=2))
    elements.append(info.foundations)
    elements.append(md_header('Takeaways', depth=2))
    elements.append(md_list(info.takeaways))
    return '\n\n'.join(elements)


@noteinfo_to_md.register
def _(info: EventInfo) -> str:
    elements : list[str] = [info.summary]
    return '\n\n'.join(elements)

@noteinfo_to_md.register
def _(info: DiscussionInfo) -> str:
    elements : list[str] = [info.summary]
    elements.append(md_header('Topic', depth=2))
    elements.append(info.topic)
    elements.append(md_header('Viewpoints', depth=2))
    elements.append(md_list(info.viewpoints))
    elements.append(md_header('Solution', depth=2))
    elements.append(info.solution)
    return '\n\n'.join(elements)
