# -*- coding: utf-8 -*-
"""
regex_extractor.py
Audit Module – Extractors
=====================

Regex‑based harvesting of endpoint candidates from JavaScript / TypeScript
source.  Heuristics are intentionally loose – high recall, low precision –
because a later LLM step performs deduplication and parameter reasoning.

Exports
-------
- Finding            (dataclass)
- extract_endpoints  (main API)
- deduplicate_findings
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    """
    A potential call site to a backend endpoint.
    """
    type: str                # 'http', 'graphql', 'ws'
    method: Optional[str]    # GET / POST / ...
    url: str                 # Full or partial URL
    file: str                # Path to source file
    line: int                # 1‑based line number
    snippet: str             # Surrounding code context
    confidence: float = 0.6  # Heuristic score


# --------------------------------------------------------------------------- #
# Regex patterns
# --------------------------------------------------------------------------- #
_RAW_URL_PATTERNS: Sequence[str] = (
    r"(?P<url>https?://[a-zA-Z0-9_\-./:?=&%#]+)",
    r"(?P<url>/api/[a-zA-Z0-9_\-./:?=&%#]+)",
)
_HTTP_PATTERNS: Sequence[str] = (
    r"fetch\(\s*(['\"])(?P<url>.+?)\1",
    r"axios\.(?P<method>get|post|put|delete|patch)\(\s*(['\"])(?P<url>.+?)\3",
)
_GRAPHQL_HINTS: Sequence[str] = (r"/graphql\b", r"operationName\s*:")
_WS_PATTERNS: Sequence[str] = (r"new\s+WebSocket\(\s*(['\"])(?P<url>ws[s]?://.+?)\1",)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def extract_endpoints(text: str, file_path: str) -> List[Finding]:
    """
    Extract potential API endpoints from JavaScript/TypeScript source code.

    This function applies multiple regex patterns to detect:
    - fetch/axios-based HTTP calls
    - WebSocket endpoints
    - GraphQL hints
    - Raw URLs (http/https)
    - Relative API paths (/api/...)

    Args:
        text (str): Source code to analyze.
        file_path (str): Absolute or relative file path (for logging).

    Returns:
        List[Finding]: List of extracted raw endpoint candidates.
    """
    results: List[Finding] = []

    try:
        # Match explicit HTTP request patterns (fetch, axios)
        for pattern in _HTTP_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line_no = text.count("\n", 0, match.start()) + 1
                url = match.group("url")
                method = match.groupdict().get("method")
                snippet = _excerpt(text, match.start(), match.end())
                results.append(Finding("http", method, url, file_path, line_no, snippet, 0.8))

        # Match raw URLs (high recall for minified JS)
        for pattern in _RAW_URL_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line_no = text.count("\n", 0, match.start()) + 1
                url = match.group("url")
                snippet = _excerpt(text, match.start(), match.end())
                results.append(Finding("http", "GET", url, file_path, line_no, snippet, 0.6))

        # Match GraphQL hints (mark file if detected)
        if any(re.search(h, text) for h in _GRAPHQL_HINTS):
            results.append(Finding("graphql", None, "", file_path, 1, "", 0.5))

        # Match WebSocket endpoints
        for pattern in _WS_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line_no = text.count("\n", 0, match.start()) + 1
                url = match.group("url")
                snippet = _excerpt(text, match.start(), match.end())
                results.append(Finding("ws", None, url, file_path, line_no, snippet, 0.8))

        # Log results
        if results:
            logger.info("Extracted %d raw findings from %s", len(results), file_path)
        else:
            logger.warning("No endpoints detected in %s", file_path)

    except Exception as e:
        logger.error("Error while extracting endpoints from %s: %s", file_path, e)

    return results


def deduplicate_findings(findings: List[Finding]) -> List[Finding]:
    """
    Remove duplicates based on (type, method, url, file, line).

    Args:
        findings (List[Finding]): Raw findings.

    Returns:
        List[Finding]: Deduplicated list (order preserved).
    """
    seen: set[tuple] = set()
    uniq: list[Finding] = []
    for f in findings:
        key = (f.type, f.method, f.url, f.file, f.line)
        if key not in seen:
            uniq.append(f)
            seen.add(key)
    logger.debug("Deduplicated to %d unique findings", len(uniq))
    return uniq


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _excerpt(text: str, start: int, end: int, ctx: int = 50) -> str:
    """
    Return `ctx` characters before/after as code excerpt.

    Args:
        text (str): Source code text.
        start (int): Match start position.
        end (int): Match end position.
        ctx (int): Context characters, default 50.

    Returns:
        str: Code excerpt.
    """
    return text[max(0, start - ctx): min(len(text), end + ctx)]
