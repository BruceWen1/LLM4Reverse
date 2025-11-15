# -*- coding: utf-8 -*-
"""
symbol_index.py
Audit Module – Resolvers
=====================

Build a minimal cross‑file symbol index (**constants, functions, classes**)
so that an LLM can look up parameter values that are spread across the code
base.  It deliberately ignores nested scopes – cheap but good enough for
static reasoning.

Example
-------
>>> index = SymbolIndex([...])
>>> index.build()
>>> index.lookup("getUserToken")
SymbolRef(name='getUserToken', file='src/auth.ts', line=12, snippet='...')
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

logger = logging.getLogger(__name__)


@dataclass
class SymbolRef:
    """
    Pointer to a symbol definition in code.
    """
    name: str  # Symbol name
    file: str  # File path
    line: int  # Line number
    snippet: str  # Code snippet


class SymbolIndex:
    """
    Lightweight map: *identifier ➜ definition* built via regex.

    Currently supports:
    - `const foo =` / `let foo =`
    - `function bar(` / `async function bar(`
    - `class Baz`
    """

    _PATTERN = re.compile(
        r"""
        ^
        (?:
            (?:export\s+)?(?:const|let|var)\s+(?P<const>[A-Za-z_][\w$]*)\s*= |
            (?:export\s+)?(?:async\s+)?function\s+(?P<func>[A-Za-z_][\w$]*)\s*\( |
            (?:export\s+)?class\s+(?P<class>[A-Za-z_][\w$]*)
        )
        """,
        re.MULTILINE | re.VERBOSE,
    )

    def __init__(self, files: Sequence[Path]) -> None:
        """
        Args:
            files (Sequence[Path]): Source files to index.
        """
        self.files = list(files)
        self._defs: Dict[str, List[SymbolRef]] = {}

    # ------------------------ public API ------------------------ #
    def build(self) -> None:
        """Populate the internal lookup table."""
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:  # pragma: no cover
                logger.warning("Skip %s (%s)", path, exc)
                continue

            for match in self._PATTERN.finditer(text):
                name = match.group("const") or match.group("func") or match.group("class")
                line_no = text.count("\n", 0, match.start()) + 1
                snippet = "\n".join(text.splitlines()[line_no - 1: line_no + 4])
                self._defs.setdefault(name, []).append(
                    SymbolRef(name, str(path), line_no, snippet)
                )

    def lookup(self, identifier: str) -> List[SymbolRef]:
        """
        Retrieve symbol definitions.

        Args:
            identifier (str): Identifier name (case‑sensitive).

        Returns:
            List[SymbolRef]: All matching definitions (can be empty).
        """
        return self._defs.get(identifier, [])
    
    def search(self, query: str) -> List[SymbolRef]:
        """
        Search for symbols containing the query substring in their snippets.

        Args:
            query (str): Substring to search for.

        Returns:
            List[SymbolRef]: All matching definitions (can be empty).
        """
        results: List[SymbolRef] = []
        query_lower = query.lower()
        for refs in self._defs.values():
            for ref in refs:
                if query_lower in ref.snippet.lower() or query_lower in ref.name.lower():
                    results.append(ref)
        return results

    # ------------------------ diagnostics ----------------------- #
    @property
    def size(self) -> int:
        """Number of unique identifiers indexed."""
        return len(self._defs)
