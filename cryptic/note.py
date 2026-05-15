#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : note.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2024

from pathlib import Path
import re

import frontmatter as fm
from rich.console import Console
from rich.markdown import Markdown

from .models import NoteSummary, PageCategory


def normalize_tag(tag: str):
    return re.sub(r'[^\w]+', '-', tag).strip('-').lower()


_TRUTHY_STR = {'true', 'yes', '1', 'on'}
_FALSY_STR = {'false', 'no', '0', 'off', ''}


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUTHY_STR:
            return True
        if v in _FALSY_STR:
            return False
    raise ValueError(f'cannot coerce {value!r} to bool')


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError(f'cannot coerce bool {value!r} to int')
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            pass
    raise ValueError(f'cannot coerce {value!r} to int')


class Note(fm.Post):

    def __init__(self,
                 path: Path | str,
                 encoding: str = "utf-8",
                 handler  = None,
                 **defaults: object):
        if isinstance(path, str):
            path = Path(path)
        self.path = path

        base = fm.load(str(path), encoding=encoding, handler=handler, **defaults)
        if 'tags' in base.metadata:
            base.metadata['tags'] = list(set(base.metadata['tags']))
        else:
            base.metadata['tags'] = list()

        super().__init__(base.content, base.handler, **base.metadata)

        if self.metadata.get('cryptic_processed') is not None:
            self.metadata['cryptic_processed'] = _coerce_bool(
                self.metadata['cryptic_processed']
            )
        if self.metadata.get('cryptic_tries') is not None:
            self.metadata['cryptic_tries'] = _coerce_int(
                self.metadata['cryptic_tries']
            )

    def save(self, path: Path | str | None = None):
        if path is None:
            path = self.path
        if isinstance(path, str):
            path = Path(path)
        with path.open('w') as fp:
            print(fm.dumps(self), file=fp)

    def normalize_tags(self):
        tags = list({normalize_tag(tag) for \
                     tag in self.metadata.get('tags', list())})
        self.metadata['tags'] = tags

    def add_tags(self, other_tags):
        tags = set(self.metadata['tags'])
        tags.update({normalize_tag(tag) for tag in other_tags})
        self.metadata['tags'] = list(tags)

    @property
    def title(self):
        return self.metadata.get('title', None)

    @title.setter
    def title(self, new_title: str):
        self.metadata['title'] = new_title

    @property
    def cryptic_processed(self):
        return self.metadata.get('cryptic_processed', False)

    @cryptic_processed.setter
    def cryptic_processed(self, value: bool):
        self.metadata['cryptic_processed'] = value

    @property
    def cryptic_tries(self) -> int | None:
        return self.metadata.get('cryptic_tries', None)

    @cryptic_tries.setter
    def cryptic_tries(self, value: int) -> None:
        self.metadata['cryptic_tries'] = value

    def to_console(self, console: Console):
        console.print('---')
        console.print(fm.YAMLHandler().export(self.metadata))
        console.print('---')
        console.print(Markdown(self.content))


class WebNote(Note):

    @property
    def category(self):
        category = self.metadata.get('category', None)
        if category is not None:
            return PageCategory[category]
        return None

    @category.setter
    def category(self, category: PageCategory):
        self.metadata['category'] = category.value


    def process_summary(self, summary: NoteSummary):
        self.category = summary.category
        self.metadata['aliases'] = [summary.metadata.title]
        self.metadata['title'] = summary.metadata.title
        self.add_tags(summary.tags)

        self.content = summary.info.to_markdown()
        summary.info.apply_frontmatter(self.metadata)
        self.cryptic_processed = True

