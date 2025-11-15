# -*- coding: utf-8 -*-
"""
code_search.py
Audit Module - Tools
=====================

LangChain tool to perform naive text search over code snippets using a prebuilt SymbolIndex.
"""

import logging
from typing import List
from langchain_core.tools import Tool
from llm4reverse.audit.resolvers.symbol_index import SymbolRef, SymbolIndex

logger = logging.getLogger(__name__)


def _make_code_search_tool(index: SymbolIndex) -> Tool:
    """
    Create a LangChain Tool that searches code snippets by substring.

    Args:
        index (SymbolIndex): Prebuilt symbol index.

    Returns:
        Tool: LangChain Tool instance.
    """
    def _search(query: str) -> str:
        """
        Perform a substring search across code snippets.

        Args:
            query (str): Substring to search.

        Returns:
            str: Markdown list of matches or a not-found message.
        """
        try:
            query = query.strip()
            logger.debug("CodeSearchTool received query: %s", query)

            refs: List[SymbolRef] = index.search(query)
            if not refs:
                return f"No matches for `{query}`"

            lines = [f"Matches for `{query}`:"]
            for r in refs:
                lines.append(f"- {r.file}:{r.line}\n```js\n{r.snippet}\n```")

            result = "\n".join(lines)
            logger.debug("Code search returned %d matches", len(refs))
            return result
        except Exception:
            logger.exception("CodeSearchTool failed for %s", query)
            return "ERROR: code search failed"

    return Tool(
        name="code_search",
        description="Given a substring, return matching file:line and snippet entries.",
        func=_search,
    )


# Backward compatibility: keep class name for imports
class CodeSearchTool:
    """
    Backward compatibility wrapper for CodeSearchTool.
    
    Use _make_code_search_tool() instead.
    """
    def __init__(self, index: SymbolIndex) -> None:
        """Initialize and create the tool."""
        self._tool = _make_code_search_tool(index)
        # Copy attributes for compatibility
        self.name = self._tool.name
        self.description = self._tool.description
    
    def __getattr__(self, name):
        """Delegate attribute access to the underlying tool."""
        return getattr(self._tool, name)


