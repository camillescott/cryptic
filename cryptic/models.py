#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : models.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2023

from enum import Enum
from textwrap import dedent
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CrypticModel(BaseModel):
   model_config = ConfigDict(use_attribute_docstrings=True)


class PageCategory(str, Enum):
    '''
    The category of the page, given its content and code. Categories are:
    article: news articles, opinion pieces, analysis pieces
    paper: scientific publications and preprints
    event: pages describing some event, like a music festival or conference
    webapp: interactive applications and calculators
    discussion: forum threads, issues, question answer pages
    software: software repositories such a github or gitlab repos, or pages for software and libraries, including sofware documentation sites
    financial: banking, investment, cryptocurrency
    product: pages for specific products
    store: online storefronts, as opposed to specific product pages
    media: multimedia pages: youtube videos, music links, art and visual media, books
    reference: general knowledge articles, encyclopedia articles, informational
    other: pages that don't fit any of the other categories well
    '''

    article = 'article'
    paper = 'paper'
    event = 'event'
    webapp = 'webapp'
    discussion = 'discussion'
    software = 'software'
    financial = 'financial'
    product = 'product'
    store = 'store'
    media = 'media'
    reference = 'reference'
    other = 'other'


PageSummary = Field(description=dedent(
'''
50 words or less focusing on the core functionality and content.
'''
))


TakeAways = Field(description=dedent(
'''
3 most important takeaways, not more than 30 words per takeaway.
'''
))


FoundationalWork = Field(description=dedent(
'''
50 words or less describing foundational work the article is built upon,
with author names and Markdown links to those works if possible.
'''
))

class PaperInfo(CrypticModel):
    category: Literal['paper']
    summary: str = PageSummary
    title: str
    authors: list[str]
    journal: str
    '''The name of the journal.'''
    abstract: str
    '''The entire abstract of the paper.'''
    doi: str
    '''format: doi.org/[remainder of DOI]'''
    takeaways: list[str] = TakeAways
    foundations: str = FoundationalWork


class ArticleInfo(CrypticModel):
    category: Literal['article']
    summary: str = PageSummary
    takeaways: list[str] = TakeAways
    foundations: str = FoundationalWork


class EventInfo(CrypticModel):
    category: Literal['event']
    summary: str = PageSummary
    start_date: str
    '''format: YYYY-MM-DD'''
    end_date: str
    '''format: YYYY-MM-DD'''


class ProductInfo(CrypticModel):
    category: Literal['product']
    summary: str = PageSummary
    name: str
    '''Concise product name, 10 words or less'''
    price: str
    '''format: $dollars.cents'''


class DiscussionInfo(CrypticModel):
    category: Literal['discussion']
    summary: str = PageSummary
    topic: str
    '''Concise summary of the topic of the discussion in 20 words or less'''
    viewpoints: list[str]
    '''Concise summary of up to 3 viewpoints in the discussion, 20 words or less each'''
    solution: str
    '''Concise summary of the proposed solution to the problem, 20 words or less'''


class MediaType(str, Enum):
    '''
    film: movies, cinema, tv shows
    music: music and music videos
    visual: illustration, photography, and so on
    interactive: games, interactive demos, etc
    book: physical and digital books
    written: poetry, short stories, etc
    '''

    film = 'film'
    music = 'music'
    visual = 'visual'
    interactive = 'interactive'
    book = 'book'
    written = 'written'


class MediaInfo(CrypticModel):
    category: Literal['media']
    summary: str = PageSummary
    artist: str
    '''Band, director, creator, or author'''
    media_type: MediaType


class SoftwareInfo(CrypticModel):
    category: Literal['software']
    summary: str = PageSummary
    language: str
    '''Primary language its written in, or Unknown'''


class ReferenceInfo(CrypticModel):
    category: Literal['reference']
    summary: str = PageSummary


NoteInfo = PaperInfo | ArticleInfo | EventInfo | ProductInfo | \
           DiscussionInfo | MediaInfo | SoftwareInfo | ReferenceInfo


class NoteSummary(CrypticModel):
    category: PageCategory

    tags: list[str]
    '''Relevant tags focusing on key topics, preferring single words over phrases. 
    Focus on the big picture. If you must use a multiword tag, separate the words with "-",
    like: word1-word2. 4 to 7 total. All lowercase.'''

    info: NoteInfo
    '''Additional information on the page, depending on its category'''


