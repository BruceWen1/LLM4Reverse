# -*- coding: utf-8 -*-
"""
Static audit (directory-level) for JS/TS sources.

This module recursively scans code files and extracts HTTP-endpoint candidates
from common client-side request idioms: fetch, XMLHttpRequest, axios, $.ajax.

Goals:
- Zero extra heavy deps (no JS parser in Python); regex-based with guards.
- Lightweight constant propagation for simple string concatenations / templates.
- Record source file + line, method guess, URL, nearby header hints, confidence.

Usage:
    from llm4reverse.tools.static_audit import scan_path
    result = scan_path(path="./dist")

Outputs (see CLI for writing JSON/MD):
    {
      "findings": [
        {
          "type": "fetch" | "xhr" | "axios" | "jquery_ajax",
          "method": "GET" | "POST" | ... | null,
          "url": "/api/v1/users" | "https://api.example.com/...",
          "source_file": "path/to/file.js",
          "line": 123,
          "headers": ["Authorization", "X-Api-Key"],
          "confidence": "high" | "medium" | "low",
          "snippet": "fetch('/api/v1/...',{method:'POST',headers:{...}})"
        },
        ...
      ],
      "stats": { "files_scanned": 42, "findings": 17, "skipped": 3 }
    }

Note:
- Designed as a pragmatic helper, not a full static analyzer.
- Prefer to combine with dynamic capture, then validate manually.

Author: LLM4Reverse
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


# -------- Regex Primitives (defensive, small windows to avoid backtracking) --------

RE_CONST_STR = re.compile(
    r"""(?x)
    \b(?:const|let|var)\s+      # declaration
    (?P<name>[A-Za-z_$][\w$]*)\s*=\s*
    (?P<q>['"])(?P<val>[^'"]{1,200}) (?P=q)\s*;?
    """
)

RE_FETCH = re.compile(
    r"""(?xs)
    fetch\s*\(\s*
      (?P<arg>[^,)\n\r]{1,300})    # first arg expression (limited)
      (?:,\s*\{(?P<cfg>[\s\S]{0,400}?)\})?   # small options object
    \)
    """
)

RE_XHR_OPEN = re.compile(
    r"""(?x)
    \.open\(\s*
      (?P<q1>['"])(?P<m>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)(?P=q1)\s*,\s*
      (?P<q2>['"])(?P<u>[^'"]{1,400})(?P=q2)
    """,
    re.IGNORECASE,
)

RE_AXIOS_M = re.compile(
    r"""(?x)
    axios\.
      (?P<m>get|post|put|delete|patch|head|options)\s*
      \(\s*(?P<q>['"])(?P<u>[^'"]{1,400})(?P=q)
    """,
    re.IGNORECASE,
)

RE_AXIOS_PLAIN = re.compile(
    r"""(?x)
    \baxios\s*\(\s*
      (?P<q>['"])(?P<u>[^'"]{1,400})(?P=q)
    """,
)

RE_JQ_AJAX = re.compile(
    r"""(?xs)
    \$\.ajax\s*\(\s*\{ (?P<cfg>[\s\S]{0,500}) \}\s*\)
    """
)

RE_CFG_METHOD = re.compile(r"""(?x)\b(method|type)\s*:\s*['"]([A-Za-z]+)['"]""")
RE_CFG_URL = re.compile(r"""(?x)\burl\s*:\s*['"]([^'"]{1,400})['"]""")
RE_CFG_HEADERS_BLOCK = re.compile(r"""(?xs)\bheaders\s*:\s*\{([\s\S]{0,400})\}""")
RE_HEADER_KEY = re.compile(r"""(?x)['"]([A-Za-z-]{2,40})['"]\s*:""")

RE_AXIOS_CREATE_BASE = re.compile(
    r"""(?x)axios\.create\(\s*\{\s*baseURL\s*:\s*['"]([^'"]{1,200})['"]""",
    re.IGNORECASE,
)

RE_TEMPLATE = re.compile(r"`([^`]{1,400})`")


@dataclass
class Finding:
    type: str
    method: Optional[str]
    url: str
    source_file: str
    line: int
    headers: List[str]
    confidence: str
    snippet: str


# -------- Helpers --------

def _collect_constants(text: str) -> Dict[str, str]:
    """Collect simple const/let/var string-literal bindings."""
    consts: Dict[str, str] = {}
    for m in RE_CONST_STR.finditer(text):
        consts[m.group("name")] = m.group("val")
    return consts


def _subst_expr(expr: str, consts: Dict[str, str]) -> str:
    """Very lightweight expression resolver for:
    - simple identifiers replaced by known string consts
    - 'a' + '/b' + VAR  concatenations
    - template literals with ${VAR}
    """
    s = expr.strip()

    # template literal
    t = RE_TEMPLATE.search(s)
    if t:
        content = t.group(1)
        # replace ${VAR} with known consts
        content = re.sub(
            r"\$\{([A-Za-z_$][\w$]*)\}",
            lambda mm: consts.get(mm.group(1), mm.group(0)),
            content,
        )
        return content

    # quoted string
    if (len(s) >= 2) and (s[0] in "\"'") and (s[-1] == s[0]):
        return s[1:-1]

    # concatenation: split by + and try to fold literals/consts
    parts = [p.strip() for p in s.split("+")]
    out = []
    for p in parts:
        if (len(p) >= 2) and (p[0] in "\"'") and (p[-1] == p[0]):
            out.append(p[1:-1])
        elif p in consts:
            out.append(consts[p])
        else:
            # unknown piece, keep symbol to show it's unresolved
            out.append("${" + p + "}")
    return "".join(out)


def _guess_confidence(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return "high"
    if url.startswith("/api/") or url.startswith("/ajax/"):
        return "high"
    if url.startswith("/"):
        return "medium"
    return "low"


def _headers_from_cfg(cfg: str) -> List[str]:
    if not cfg:
        return []
    block = RE_CFG_HEADERS_BLOCK.search(cfg)
    if not block:
        return []
    return list({m.group(1) for m in RE_HEADER_KEY.finditer(block.group(1))})


def _line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# -------- File analysis --------

def analyze_file(text: str, file_path: str, base_urls: List[str]) -> List[Finding]:
    """Analyze a single file and return list of candidate findings."""
    consts = _collect_constants(text)
    findings: List[Finding] = []

    # axios.create baseURL (collect for info; not used to join URL here)
    for m in RE_AXIOS_CREATE_BASE.finditer(text):
        base_urls.append(m.group(1))

    # fetch(...)
    for m in RE_FETCH.finditer(text):
        arg = (m.group("arg") or "").strip()
        cfg = m.group("cfg") or ""
        url = _subst_expr(arg, consts)
        method_m = RE_CFG_METHOD.search(cfg)
        method = method_m.group(2).upper() if method_m else None
        headers = _headers_from_cfg(cfg)
        findings.append(
            Finding(
                type="fetch",
                method=method,
                url=url,
                source_file=file_path,
                line=_line_number(text, m.start()),
                headers=headers,
                confidence=_guess_confidence(url),
                snippet=text[m.start() : min(len(text), m.end() + 200)].splitlines()[0][:200],
            )
        )

    # xhr.open(...)
    for m in RE_XHR_OPEN.finditer(text):
        method = (m.group("m") or "").upper()
        url = m.group("u")
        findings.append(
            Finding(
                type="xhr",
                method=method,
                url=url,
                source_file=file_path,
                line=_line_number(text, m.start()),
                headers=[],
                confidence=_guess_confidence(url),
                snippet=text[m.start() : min(len(text), m.end() + 200)].splitlines()[0][:200],
            )
        )

    # axios.METHOD('url', ...)
    for m in RE_AXIOS_M.finditer(text):
        method = (m.group("m") or "").upper()
        url = m.group("u")
        findings.append(
            Finding(
                type="axios",
                method=method,
                url=url,
                source_file=file_path,
                line=_line_number(text, m.start()),
                headers=[],
                confidence=_guess_confidence(url),
                snippet=text[m.start() : min(len(text), m.end() + 200)].splitlines()[0][:200],
            )
        )

    # axios('url', ...)
    for m in RE_AXIOS_PLAIN.finditer(text):
        url = m.group("u")
        findings.append(
            Finding(
                type="axios",
                method=None,
                url=url,
                source_file=file_path,
                line=_line_number(text, m.start()),
                headers=[],
                confidence=_guess_confidence(url),
                snippet=text[m.start() : min(len(text), m.end() + 200)].splitlines()[0][:200],
            )
        )

    # $.ajax({ ... })
    for m in RE_JQ_AJAX.finditer(text):
        cfg = m.group("cfg") or ""
        method_m = RE_CFG_METHOD.search(cfg)
        method = method_m.group(2).upper() if method_m else None
        url_m = RE_CFG_URL.search(cfg)
        url = url_m.group(1) if url_m else ""
        headers = _headers_from_cfg(cfg)
        if not url:
            continue
        findings.append(
            Finding(
                type="jquery_ajax",
                method=method,
                url=url,
                source_file=file_path,
                line=_line_number(text, m.start()),
                headers=headers,
                confidence=_guess_confidence(url),
                snippet=("$.ajax({" + cfg[:160].replace("\n", " ") + " ...})"),
            )
        )

    return findings


# -------- Path scan --------

DEFAULT_INCLUDES = ["**/*.js", "**/*.mjs", "**/*.ts", "**/*.jsx", "**/*.tsx"]


def _iter_files(root: Path, includes: List[str], excludes: List[str], max_files: int) -> Iterable[Path]:
    seen: set[Path] = set()
    for pat in includes:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            # exclude
            skip = any(fnmatch.fnmatch(str(p), ex) for ex in excludes)
            if skip:
                continue
            if p in seen:
                continue
            seen.add(p)
            yield p
            if len(seen) >= max_files:
                return


def scan_path(
    path: str,
    includes: Optional[List[str]] = None,
    excludes: Optional[List[str]] = None,
    max_files: int = 1000,
    max_bytes: int = 1_500_000,
) -> Dict[str, object]:
    """
    Scan a directory for HTTP endpoint candidates in client-side code.

    Args:
        path: Directory to scan.
        includes: Glob patterns (default: DEFAULT_INCLUDES).
        excludes: Glob patterns to exclude.
        max_files: Limit files scanned.
        max_bytes: Per-file read cap to avoid huge bundles.

    Returns:
        Dict with "findings" and "stats".
    """
    root = Path(path).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Path not found or not a directory: {root}")

    includes = includes or DEFAULT_INCLUDES
    excludes = excludes or []
    findings: List[Finding] = []
    base_urls: List[str] = []

    files = list(_iter_files(root, includes, excludes, max_files))
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            if len(text) > max_bytes:
                text = text[:max_bytes]
            findings.extend(analyze_file(text, str(fp), base_urls))
        except Exception as e:  # noqa: BLE001
            # skip unreadable files; could log if needed
            continue

    # de-duplicate (method + url + type)
    dedup: Dict[Tuple[Optional[str], str, str], Finding] = {}
    for f in findings:
        key = (f.method, f.url, f.type)
        # keep first hit; could also accumulate occurrences if needed
        if key not in dedup:
            dedup[key] = f

    out = {
        "findings": [f.__dict__ for f in dedup.values()],
        "stats": {"files_scanned": len(files), "findings": len(dedup), "skipped": 0},
        "hints": {"axios_baseURLs": list(set(base_urls))},
    }
    return out
