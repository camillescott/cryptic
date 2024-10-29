#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : chat.py
# License: MIT
# Author : Camille Scott <camille.scott.w@gmail.com>
# Date   : 23.10.2024
# (c) Camille Scott, 2024


from openai import OpenAI

from .models import NoteSummary


OPENAI_MODELS = {
    'gpt-4o',
    'gpt-4o-mini'
}


def summarize_page(content: str,
                   model: str = 'gpt-4o-mini'):
    client = OpenAI()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", 
             "content": "You are an expert at structured data extraction. You will be given unstructured source from a webpage and should convert it to the given format."},
            {"role": "user", "content": content}
        ],
        response_format=NoteSummary,
    )
    return completion.choices[0].message.parsed, completion
