#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : models.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2023

from enum import Enum
from textwrap import dedent
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .markdown import (
    MdFrontmatter,
    MdSection,
    MdSkip,
    apply_frontmatter as _apply_frontmatter,
    render as _render,
)


class CrypticModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

    def to_markdown(self) -> str:
        return _render(self)

    def apply_frontmatter(self, target: dict[str, Any]) -> None:
        _apply_frontmatter(self, target)


class PageCategory(str, Enum):
    '''
    The category of the page, given its content and context.
    Categories:
      article: news articles, opinion pieces, analysis pieces, blog posts
      paper: scientific publications and preprints (incl. arXiv, bioRxiv)
      event: pages describing a single event (festival, conference, talk)
      space: a physical place — bar, restaurant, cafe, venue, gallery, etc.
      webapp: interactive applications, calculators, demos
      discussion: forum threads, issues, Q&A pages, comment threads
      software: code repos (github/gitlab), package pages, software docs
      financial: banking, investing, cryptocurrency, market pages
      product: a page for one specific product
      store: a storefront listing many products
      media: youtube videos, music, art, books, podcasts
      reference: encyclopedia-style, definitional, or look-up content
      other: only when none of the above is a defensible fit

    Disambiguation:
    - Prefer the more specific category. A scientific blog post is
      `article`, not `reference`. A GitHub README is `software`, not
      `reference`. A specific iPhone listing is `product`, the Apple
      store homepage is `store`.
    - `paper` is for the artifact itself; a write-up *about* a paper
      is `article`.
    - `discussion` requires actual back-and-forth (multiple participants
      or replies). A single-author Q&A explainer is `reference`.
    - `space` is the venue itself (where you go). A page advertising
      one specific dated performance at a venue is `event`, not `space`.
    '''

    article = 'article'
    paper = 'paper'
    event = 'event'
    space = 'space'
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
Single paragraph describing what the page is about. 50 words or less.
No preamble like "this page discusses". Write declaratively.
'''
).strip())


TakeAways = Field(description=dedent(
'''
Up to 3 concrete takeaways — specific claims, findings, or conclusions
that someone reading only the takeaways would still learn the gist.
30 words or less each. Return an empty list if the source has no
actionable claims.
'''
).strip())


FoundationalWork = Field(description=dedent(
'''
Up to 50 words describing prior work this builds on, with author names
and Markdown links *only when the source explicitly cites them with
URLs*. Use 'none' if the source does not cite prior work.
'''
).strip())


class PaperInfo(CrypticModel):
    category: Annotated[Literal['paper'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    original_title: Annotated[
        str,
        MdSkip(),
        MdFrontmatter(key='aliases', transform=lambda v: [v]),
    ]
    '''The paper's title exactly as it appears in the source (preserve
    capitalization and punctuation). Distinct from the note's filename title.'''
    authors: Annotated[list[str], MdSkip(), MdFrontmatter(key='author')]
    '''Author names in the order shown in the byline. Names only, no
    affiliations or email addresses.'''
    journal: Annotated[str, MdSkip(), MdFrontmatter(key='journal')]
    '''Journal or preprint server name (e.g., "Nature", "arXiv"). Use
    'unknown' if not stated.'''
    abstract: Annotated[
        str,
        MdSection(),
        Field(serialization_alias='Abstract'),
    ]
    '''The complete abstract verbatim, or 'unknown' if no abstract is
    present.'''
    doi: Annotated[str, MdSkip(), MdFrontmatter(key='doi')]
    '''DOI as `doi.org/<suffix>`, or an arXiv id (`arxiv.org/abs/<id>`),
    or 'unknown'. Do not invent a DOI.'''
    foundations: Annotated[
        str,
        MdSection(),
        Field(serialization_alias='Foundational Work'),
    ] = FoundationalWork
    takeaways: Annotated[
        list[str],
        MdSection(style='bullets'),
        Field(serialization_alias='Takeaways'),
    ] = TakeAways


class ArticleInfo(CrypticModel):
    category: Annotated[Literal['article'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    foundations: Annotated[
        str,
        MdSection(),
        Field(serialization_alias='Foundational Work'),
    ] = FoundationalWork
    takeaways: Annotated[
        list[str],
        MdSection(style='bullets'),
        Field(serialization_alias='Takeaways'),
    ] = TakeAways


class EventInfo(CrypticModel):
    category: Annotated[Literal['event'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    start_datetime: Annotated[str, MdSkip(), MdFrontmatter(key='start_datetime')]
    '''Event start date and time as YYYY-MM-DDTHH:MM. Use the local timezone of the event.
    If the time is not stated, format as YYYY-MM-DD. 'unknown' if unavailable.'''
    end_datetime: Annotated[str, MdSkip(), MdFrontmatter(key='end_datetime')]
    '''Event end date and time as YYYY-MM-DDTHH:MM. Use the local timezone of the event.
    If the time is not stated, format as YYYY-MM-DD. 'unknown' if unavailable.'''
    location: Annotated[str, MdSkip(), MdFrontmatter(key='location')]
    '''Event location as a single line, or 'unknown' if unavailable.'''


class ProductInfo(CrypticModel):
    category: Annotated[Literal['product'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    name: Annotated[
        str,
        MdSkip(),
        MdFrontmatter(key='title'),
        MdFrontmatter(key='aliases', transform=lambda v: [v]),
    ]
    '''Concise product name, 10 words or less'''
    price: Annotated[str, MdSkip(), MdFrontmatter(key='price')]
    '''Price as listed: e.g., '$19.99', '€15', 'free', 'contact sales',
    or 'unknown'. Preserve the currency symbol from the source.'''


class DiscussionInfo(CrypticModel):
    category: Annotated[Literal['discussion'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    topic: Annotated[str, MdSection(), Field(serialization_alias='Topic')]
    '''Concise summary of the topic of the discussion in 20 words or less'''
    viewpoints: Annotated[
        list[str],
        MdSection(style='bullets'),
        Field(serialization_alias='Viewpoints'),
    ]
    '''Concise summary of up to 3 viewpoints in the discussion, 20 words or less each'''
    solution: Annotated[str, MdSection(), Field(serialization_alias='Solution')]
    '''The proposed or accepted solution in 20 words or less. Use
    'unresolved' if the thread did not converge on one.'''


class MediaType(str, Enum):
    '''
    film: movies, cinema, tv shows
    music: songs, albums, music videos
    visual: illustration, photography, painting, sculpture
    interactive: games, interactive demos, playable simulations, generative art
    book: physical and digital books
    written: poetry, short stories, essays, fiction excerpts
    '''

    film = 'film'
    music = 'music'
    visual = 'visual'
    interactive = 'interactive'
    book = 'book'
    written = 'written'


class MediaInfo(CrypticModel):
    category: Annotated[Literal['media'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    artist: Annotated[str, MdSkip(), MdFrontmatter(key='artist')]
    '''Band, director, creator, or author'''
    media_type: Annotated[MediaType, MdSkip(), MdFrontmatter(key='media_type')]


class SoftwareInfo(CrypticModel):
    category: Annotated[Literal['software'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    language: Annotated[
        str,
        MdSkip(),
        MdFrontmatter(key='prog_lang', transform=str.lower),
    ]
    '''Predominant implementation language (as advertised by the project,
    or whichever has the most code). Use 'unknown' if not stated.'''
    authors: Annotated[list[str], MdSkip(), MdFrontmatter(key='author')]
    '''Primary authors or maintainers, maximum 5'''


class ReferenceInfo(CrypticModel):
    category: Annotated[Literal['reference'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary


class SpaceInfo(CrypticModel):
    category: Annotated[Literal['space'], MdSkip()]
    summary: Annotated[str, MdSection()] = PageSummary
    name: Annotated[
        str,
        MdSkip(),
        MdFrontmatter(key='title'),
        MdFrontmatter(key='aliases', transform=lambda v: [v]),
    ]
    '''Name of the place, 10 words or less.'''
    city: Annotated[str, MdSkip(), MdFrontmatter(key='city')]
    '''City the place is located in, or 'unknown' if not stated.'''
    address: Annotated[str, MdSkip(), MdFrontmatter(key='address')]
    '''Full street address as a single line, or 'unknown' if not stated.'''


NoteInfo = PaperInfo | ArticleInfo | EventInfo | ProductInfo | \
           DiscussionInfo | MediaInfo | SoftwareInfo | ReferenceInfo | \
           SpaceInfo


class BaseNoteSummary(CrypticModel):
    tags: list[str]
    '''Relevant topical tags focusing on subject matter, preferring single
    words over phrases. 4 to 7 total, all lowercase. Multiword tags use
    hyphens: word1-word2. Avoid tags that duplicate the category (don't
    tag a `paper` note with "paper" or "research"); avoid platform and
    publisher tags ("github", "youtube", "substack").'''


class NoteMetadata(CrypticModel):
    title: str
    '''Succinct, descriptive title for the note — capture the page's
    actual subject, not the site's name. 10 words or less. Will be used
    as the filename slug.'''


class NoteSummary(BaseNoteSummary):
    '''Structured summary of a single web page. Pick `category` first;
    the `info` block must match that category (the model is responsible
    for selecting the right variant).'''
    metadata: NoteMetadata
    category: PageCategory
    info: NoteInfo
    '''Category-specific fields. The discriminator field `info.category`
    must match the top-level `category`.'''


class SoftwareSummary(BaseNoteSummary):
    info: SoftwareInfo


class ReferenceSummary(BaseNoteSummary):
    info: ReferenceInfo


def summary_schema_from_category(category: PageCategory):
    for subschema in BaseNoteSummary.__subclasses__():
        if subschema is NoteSummary:
            continue
        if subschema.__annotations__['info'].__annotations__['category'].__args__[0] == category.value:
            return subschema
    return NoteSummary
