#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : config.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>

from __future__ import annotations

from importlib.resources import files as _pkg_files
import os
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


DEFAULT_MODELS = ['gpt-5.4-mini', 'gpt-5.4-nano-2026-03-17']
DEFAULT_MODEL = 'gpt-5.4-mini'

ReasoningLevel = Literal['low', 'medium', 'high', 'xhigh']
REASONING_LEVELS: tuple[ReasoningLevel, ...] = ('low', 'medium', 'high', 'xhigh')
DEFAULT_REASONING: ReasoningLevel = 'medium'


def _xdg_default_config_path() -> Path:
    base = os.environ.get('XDG_CONFIG_HOME')
    root = Path(base) if base else Path.home() / '.config'
    return root / 'cryptic' / 'config.yaml'


def _packaged_prompt_text() -> str:
    return (_pkg_files('cryptic') / 'prompts' / 'categorize.txt').read_text(encoding='utf-8').strip()


class OpenAICfg(BaseModel):
    models: list[str] = Field(default_factory=lambda: list(DEFAULT_MODELS))
    default_model: str = DEFAULT_MODEL
    default_reasoning: ReasoningLevel = DEFAULT_REASONING

    @model_validator(mode='after')
    def _default_in_models(self) -> Self:
        if self.default_model not in self.models:
            raise ValueError(
                f'default_model {self.default_model!r} is not in openai.models {self.models}'
            )
        return self


class PromptCfg(BaseModel):
    path: Path | None = None
    text: str | None = None

    @model_validator(mode='after')
    def _resolve(self) -> Self:
        if self.path is not None and self.text is not None:
            raise ValueError('prompt: set exactly one of `path` or `text`, not both')
        if self.path is not None:
            resolved = Path(self.path).expanduser().resolve()
            self.text = resolved.read_text(encoding='utf-8').strip()
        return self


class VaultCfg(BaseModel):
    input_dir: Path
    prefix_dir: Path
    output_dir: str
    '''Python format string for the directory the processed note is written
    to. Keys reference frontmatter values on the *processed* note (e.g.
    `{category}`, `{author[0]}`). The resolved path must be a child of
    `prefix_dir`.'''
    originals_dir: str
    '''Python format string for the directory the unmodified original is
    archived to. Keys reference frontmatter values on the *input* note
    as the service first observes it. The resolved path must be a child
    of `prefix_dir`.'''
    name: str | None = None

    @model_validator(mode='after')
    def _expand(self) -> Self:
        self.input_dir = Path(self.input_dir).expanduser().resolve()
        self.prefix_dir = Path(self.prefix_dir).expanduser().resolve()
        return self

    def resolve_output(self, metadata: dict[str, Any]) -> Path:
        return self._resolve(self.output_dir, metadata, 'output_dir')

    def resolve_originals(self, metadata: dict[str, Any]) -> Path:
        return self._resolve(self.originals_dir, metadata, 'originals_dir')

    def _resolve(self, template: str, metadata: dict[str, Any], field: str) -> Path:
        try:
            formatted = template.format_map(metadata)
        except KeyError as e:
            raise ValueError(
                f'{field} template {template!r} references missing key {e}'
            ) from e
        candidate = Path(formatted).expanduser().resolve()
        if not candidate.is_relative_to(self.prefix_dir):
            raise ValueError(
                f'{field} resolved to {candidate} which is not under '
                f'prefix_dir {self.prefix_dir}'
            )
        return candidate


class ServiceCfg(BaseModel):
    vaults: dict[str, VaultCfg]
    max_concurrent: int = 3
    max_tries: int = 3
    pickup_delay_seconds: float = 3.0

    @model_validator(mode='after')
    def _check(self) -> Self:
        if not self.vaults:
            raise ValueError('service.vaults must define at least one vault')
        seen: dict[Path, str] = {}
        for name, vault in self.vaults.items():
            vault.name = name
            if vault.input_dir in seen:
                raise ValueError(
                    f'vaults {seen[vault.input_dir]!r} and {name!r} share '
                    f'input_dir {vault.input_dir}; input_dirs must be distinct'
                )
            seen[vault.input_dir] = name
        if self.max_concurrent < 1:
            raise ValueError('service.max_concurrent must be >= 1')
        if self.max_tries < 1:
            raise ValueError('service.max_tries must be >= 1')
        if self.pickup_delay_seconds < 0:
            raise ValueError('service.pickup_delay_seconds must be >= 0')
        return self


class AppConfig(BaseModel):
    openai: OpenAICfg = Field(default_factory=OpenAICfg)
    prompt: PromptCfg = Field(default_factory=PromptCfg)
    service: ServiceCfg | None = None

    @model_validator(mode='after')
    def _default_prompt(self) -> Self:
        if self.prompt.text is None and self.prompt.path is None:
            self.prompt = PromptCfg(text=_packaged_prompt_text())
        return self

    @classmethod
    def load(cls, path: Path | None) -> AppConfig:
        if path is not None:
            path = Path(path).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f'config file not found: {path}')
            return cls._from_file(path)

        default = _xdg_default_config_path()
        if default.exists():
            return cls._from_file(default)

        return cls()

    @classmethod
    def _from_file(cls, path: Path) -> AppConfig:
        with path.open('r', encoding='utf-8') as fp:
            raw = yaml.safe_load(fp) or {}
        try:
            return cls.model_validate(raw)
        except ValidationError as e:
            raise ValueError(f'invalid config at {path}:\n{e}') from e

    def require_service(self) -> ServiceCfg:
        if self.service is None:
            raise ValueError(
                'service config required: add a `service:` section to your config.yaml '
                f'(default location: {_xdg_default_config_path()})'
            )
        return self.service
