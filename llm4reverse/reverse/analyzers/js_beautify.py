# -*- coding: utf-8 -*-
"""
js_beautify.py
Reverse Module - Analyzers
=====================

JavaScript beautification and basic pattern scanning.

Patterns (conservative):
- token-like markers: token/auth/jwt
- '/api/...' path fragments
- fetch("...") URLs
- xhr.open("METHOD", "URL")
"""

from __future__ import annotations

import re
from typing import Any, Dict

import jsbeautifier


class JSBeautifyTool:
    """
    Beautify JS and run minimal regex-based hints.
    """

    def __init__(self) -> None:
        """
        Initialize beautifier with default options.
        """
        self.opts = jsbeautifier.default_options()
        self.opts.indent_size = 2

    def run(self, code: str) -> Dict[str, Any]:
        """
        Return beautified code and simple pattern matches.

        Args:
            code (str): Raw JavaScript code.

        Returns:
            Dict[str, Any]: Dictionary containing beautified code and pattern matches.
        """
        # Beautify code
        pretty = jsbeautifier.beautify(code, self.opts)
        # Run pattern matching
        patterns = {
            "token_like": re.findall(r"(token|auth|jwt)[^\n\r\"']{0,40}", code, flags=re.IGNORECASE),
            "api_paths": re.findall(r"['\"](\/api\/[^'\"\s]+)['\"]", code, flags=re.IGNORECASE),
            "fetch_calls": re.findall(r"fetch\(['\"]([^'\"\)]+)['\"]", code, flags=re.IGNORECASE),
            "xhr_open": re.findall(
                r"open\(['\"](GET|POST|PUT|DELETE)['\"],\s*['\"]([^'\"\)]+)['\"]", code, flags=re.IGNORECASE
            ),
        }
        return {"beautified": pretty, "patterns": patterns}


