#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : note.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2024

from functools import singledispatchmethod
from pathlib import Path
import re

import frontmatter as fm
from rich.console import Console
from rich.markdown import Markdown

from .markdown import noteinfo_to_md

from .models import (BaseNoteSummary,
                     NoteSummary,
                     PageCategory,
                     NoteInfo,
                     PaperInfo,
                     ArticleInfo,
                     EventInfo,
                     ProductInfo,
                     DiscussionInfo,
                     MediaInfo,
                     SoftwareInfo,
                     ReferenceInfo)


def normalize_tag(tag: str):
    return re.sub(r'[^\w]+', '-', tag).strip('-').lower()


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

    def save(self):
        with self.path.open('w') as fp:
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


    def process_summary(self, summary: BaseNoteSummary):
        if isinstance(summary, NoteSummary):
            self.category = summary.category
        self.add_tags(summary.tags)

        self.content = noteinfo_to_md(summary.info)
        self.process_info(summary.info)
        self.cryptic_processed = True

    @singledispatchmethod
    def process_info(self, info: NoteInfo):
        pass

    @process_info.register
    def _(self, info: PaperInfo):
        self.title = info.title
        self['aliases'][0] = info.title
        self['author'] = info.authors
        self['journal'] = info.journal
        self['doi'] = info.doi

    @process_info.register
    def _(self, info: ArticleInfo):
        pass

    @process_info.register
    def _(self, info: EventInfo):
        self['start_date'] = info.start_date
        self['end_date'] = info.end_date

    @process_info.register
    def _(self, info: ProductInfo):
        self.title = info.name
        self['aliases'][0] = info.name
        self['price'] = info.price

    @process_info.register
    def _(self, info: MediaInfo):
        self['media_type'] = info.media_type.value
        self['artist'] = info.artist

    @process_info.register
    def _(self, info: SoftwareInfo):
        self['prog_lang'] = info.language.lower()
        self['author'] = info.authors

