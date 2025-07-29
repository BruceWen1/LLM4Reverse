# -*- coding: utf-8 -*-
"""
Minimal OpenAI-compatible chat client.

- Explicit, expert-friendly design
- Raises on missing API key or malformed response
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


class OpenAIChatClient:
    """Thin wrapper around OpenAI (or compatible) chat completions."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM reasoning.")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=api_key, base_url=base_url or os.getenv("OPENAI_BASE_URL"))

    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.2, max_tokens: int = 12800) -> str:
        """Send a chat completion request and return assistant content."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        print(f"Chat return: {resp}")
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            raise RuntimeError("LLM response is empty or malformed.")
        return resp.choices[0].message.content
