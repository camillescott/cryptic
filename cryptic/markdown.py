#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : markdown.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel
from pydantic.fields import FieldInfo


Style = Literal['paragraph', 'bullets', 'numbered']


@dataclass(frozen=True)
class MdSection:
    """Render this field as a section in the note body.

    Header text comes from the field's `serialization_alias`. If neither
    `header` nor `serialization_alias` is set, the section is emitted
    without a header.

    When `skip_empty` is True (the default), a string value of 'unknown'
    or 'none' (case-insensitive) also suppresses the entire section,
    header included. Truly empty values (None, empty string, empty list)
    are always suppressed regardless of `skip_empty`.
    """
    depth: int = 2
    style: Style = 'paragraph'
    header: str | None = None
    skip_empty: bool = True


@dataclass(frozen=True)
class MdSkip:
    """Explicit marker: this field is intentionally not in the body."""
    pass


@dataclass(frozen=True)
class MdFrontmatter:
    """Map this field into the note's YAML frontmatter under `key`.

    A field can carry multiple MdFrontmatter annotations to write the
    same source value to several frontmatter keys.
    """
    key: str
    transform: Callable[[Any], Any] | None = None


def render(model: BaseModel) -> str:
    chunks: list[str] = []
    for name, fi in type(model).model_fields.items():
        meta = _md_meta(fi)
        if meta is None or isinstance(meta, MdSkip):
            continue
        value = getattr(model, name)
        if _should_skip(value, meta):
            continue
        chunks.append(_render_section(value, meta, _header_for(meta, fi)))
    return '\n\n'.join(chunks)


def apply_frontmatter(model: BaseModel, target: dict[str, Any]) -> None:
    dumped = model.model_dump()
    for name, fi in type(model).model_fields.items():
        value = dumped.get(name)
        for m in fi.metadata:
            if not isinstance(m, MdFrontmatter):
                continue
            target[m.key] = m.transform(value) if m.transform else value


def _md_meta(fi: FieldInfo) -> MdSection | MdSkip | None:
    for m in fi.metadata:
        if isinstance(m, (MdSection, MdSkip)):
            return m
    return None


def _header_for(meta: MdSection, fi: FieldInfo) -> str | None:
    return meta.header or fi.serialization_alias


_EMPTY_SENTINELS = frozenset({'unknown', 'none'})


def _should_skip(value: Any, meta: MdSection) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple)) and not value:
        return True
    if meta.skip_empty and isinstance(value, str):
        if value.strip().lower() in _EMPTY_SENTINELS:
            return True
    return False


def _render_section(value: Any, meta: MdSection, header: str | None) -> str:
    parts: list[str] = []
    if header:
        parts.append('#' * meta.depth + ' ' + header)
    if meta.style == 'paragraph':
        parts.append(str(value))
    elif meta.style == 'bullets':
        parts.append('\n'.join(f'- {item}' for item in value))
    elif meta.style == 'numbered':
        parts.append('\n'.join(f'{i + 1}. {item}' for i, item in enumerate(value)))
    return '\n\n'.join(parts)
