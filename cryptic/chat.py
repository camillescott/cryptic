#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : chat.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2024

from typing import Type

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from .models import BaseNoteSummary, NoteSummary


async def summarize_page(
    client: AsyncOpenAI,
    content: str,
    *,
    model: str,
    system_prompt: str,
    reasoning: str,
    schema: Type[BaseNoteSummary] = NoteSummary,
) -> tuple[BaseNoteSummary | None, ChatCompletion]:
    completion = await client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        response_format=schema,
        reasoning_effort=reasoning,
    )
    return completion.choices[0].message.parsed, completion
