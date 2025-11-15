# -*- coding: utf-8 -*-
"""
symbol_lookup.py
Audit Module - Tools
=====================

LangChain tool to look up symbol definitions from a SymbolIndex.
"""

import logging
from typing import List
from langchain_core.tools import Tool
from llm4reverse.audit.resolvers.symbol_index import SymbolRef, SymbolIndex

logger = logging.getLogger(__name__)


def _make_symbol_lookup_tool(index: SymbolIndex) -> Tool:
    """
    Create a LangChain Tool that looks up symbol definitions by name.

    Args:
        index (SymbolIndex): Symbol index instance used for lookups.

    Returns:
        Tool: LangChain Tool instance.
    """
    def _lookup(symbol: str) -> str:
        """
        Look up symbol definitions synchronously.

        Args:
            symbol (str): Symbol name to search for.

        Returns:
            str: Markdown list of symbol definitions or a not-found message.
        """
        try:
            symbol = symbol.strip()
            logger.debug("SymbolLookupTool received query: %s", symbol)

            refs: List[SymbolRef] = index.lookup(symbol)
            if not refs:
                return f"No definitions found for `{symbol}`"

            lines = [f"Definitions for `{symbol}`:"]
            for r in refs:
                lines.append(f"- {r.file}:{r.line}\n```js\n{r.snippet}\n```")

            result = "\n".join(lines)
            logger.debug("Symbol lookup found %d definitions for %s", len(refs), symbol)
            return result
        except Exception:
            logger.exception("SymbolLookupTool failed for %s", symbol)
            return "ERROR: symbol lookup failed"

    return Tool(
        name="symbol_lookup",
        description="Given a symbol name, return file:line and code snippet definitions.",
        func=_lookup,
    )


# Backward compatibility: keep class name for imports
class SymbolLookupTool:
    """
    Backward compatibility wrapper for SymbolLookupTool.
    
    Use _make_symbol_lookup_tool() instead.
    """
    def __init__(self, index: SymbolIndex) -> None:
        """Initialize and create the tool."""
        self._tool = _make_symbol_lookup_tool(index)
        # Copy attributes for compatibility
        self.name = self._tool.name
        self.description = self._tool.description
    
    def __getattr__(self, name):
        """Delegate attribute access to the underlying tool."""
        return getattr(self._tool, name)


