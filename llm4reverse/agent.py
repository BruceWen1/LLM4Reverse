# -*- coding: utf-8 -*-
"""
Agent orchestration for LLM4Reverse.

- Loads a fixed, explicit system prompt (embedded below).
- Sends structured evidence to an OpenAI-compatible chat API.
- Returns a concise reverse report in Markdown.

Environment:
- OPENAI_API_KEY    required when reasoning is enabled
- OPENAI_BASE_URL   optional (OpenAI-compatible)
- OPENAI_MODEL      optional (default gpt-4o-mini)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm_client import OpenAIChatClient


# Embedded system prompt to avoid packaging extra data files.
_SYSTEM_PROMPT = """You are a senior reverse engineer specializing in modern web front-ends.
You will receive:
1) A summary of network requests and console logs
2) Optional HTML/JS snippets
3) Optional AST findings (identifiers, literals, fetch/XHR URLs)

TASK:
- Identify potential API endpoints and parameters
- Infer auth schemes or signatures if hints exist
- Highlight obfuscation patterns and next steps
- Produce a concise reverse report with concrete actions

Output sections:
- Targets
- Findings (APIs, Params, Headers, Tokens)
- Risks / Weak points
- Suggested next steps
"""


class ReverseAgent:
    """LLM-backed reverse engineering agent."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None) -> None:
        """Initialize the LLM client with optional overrides."""
        self.client = OpenAIChatClient(model=model, base_url=base_url)

    def reason(self, evidence: Dict[str, Any]) -> str:
        """Run LLM reasoning on evidence and return a Markdown report.

        Args:
            evidence: Dict containing browser capture, js analysis, AST, etc.

        Returns:
            Markdown string with actionable reverse findings.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Evidence JSON:\n{evidence}"},
        ]
        return self.client.chat(messages, temperature=0.2, max_tokens=12800)
