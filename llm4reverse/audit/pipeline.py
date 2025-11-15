# -*- coding: utf-8 -*-
"""
pipeline.py
Audit Module
=====================

Static source–code audit orchestrator.

Flow
----
1. Walk a directory tree and collect source files.
2. Extract possible endpoints (HTTP / GraphQL / WS) via regex heuristics.
3. Build an index of symbols for cross‑file reasoning.
4. (Optional) Ask an LLM agent (ReAct) to enrich each finding with
   headers / params / payload schema, using the index as a tool.
5. Persist a JSON + Markdown report and the full LLM trace.

Example
-------
python -m llm4reverse.audit.pipeline \
    --path ./webapp \
    --include .js .ts \
    --exclude node_modules tests \
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Sequence, Set

from llm4reverse.audit.extractors.regex_extractor import (
    Finding,
    deduplicate_findings,
    extract_endpoints,
)
from llm4reverse.audit.resolvers.symbol_index import SymbolIndex
from llm4reverse.audit.scanner import iter_source_files
from llm4reverse.audit import report as report_writer
from llm4reverse.audit.agents.endpoint_agent import run_trace

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Core orchestration
# --------------------------------------------------------------------------- #
def run_static_audit(
    path: str,
    include: Sequence[str],
    exclude: Optional[Sequence[str]] = None,
) -> None:
    """
    Perform a static audit and LLM enrichment.

    Args:
        path (str): Root directory to analyse.
        include (Sequence[str]): File extensions to include (e.g. ['.js']).
        exclude (Optional[Sequence[str]]): Directory names to skip.

    Raises:
        RuntimeError: On scanning or extraction failure.
    """
    t0 = time.perf_counter()
    # Normalize file extensions and exclude directories
    include: Set[str] = {ext.lower() for ext in include}
    exclude: Set[str] = set(exclude or [])

    logger.info("Static audit started (dir=%s)", path)

    # Collect source files
    files = list(iter_source_files(path, include, exclude))
    if not files:
        raise RuntimeError("No source files found – aborting.")
    logger.info("Collected %d source files", len(files))

    # Extract endpoints using regex
    findings: List[Finding] = []
    for fp in files:
        try:
            findings.extend(
                extract_endpoints(fp.read_text(encoding="utf-8", errors="ignore"), str(fp))
            )
        except Exception as exc:
            logger.error("Failed reading %s: %s", fp, exc)

    # Deduplicate findings
    findings = deduplicate_findings(findings)
    if not findings:
        raise RuntimeError("No endpoints detected – nothing to audit.")
    logger.info("Extracted %d raw findings", len(findings))

    # Build symbol index
    index = SymbolIndex(files)
    index.build()
    logger.info("Symbol index built (%d symbols)", index.size)

    # LLM enrichment (always enabled)
    findings, trace = run_trace(findings, index, model_name=None)
    Path(path, "audit_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2)
    )
    logger.info("LLM enrichment complete")

    # Write report
    report_writer.write_audit_report(findings, Path(path))
    logger.info("Audit completed in %.2fs", time.perf_counter() - t0)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args() -> argparse.Namespace:
    """
    Parse and return CLI arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    p = argparse.ArgumentParser(description="Static audit (LLM-powered).")
    p.add_argument("--path", required=True, help="Path to local code directory")
    p.add_argument(
        "--include",
        default=".js,.ts,.jsx,.tsx",
        help="Comma-separated glob patterns to include",
    )
    p.add_argument(
        "--exclude",
        default="node_modules,dist,build,.git",
        help="Comma-separated directory names to exclude",
    )
    return p.parse_args()


def main() -> None:
    """
    Main entry point for CLI usage.

    This function configures logging, parses command-line arguments,
    and executes the static audit workflow.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_static_audit(
        path=args.path,
        include=args.include.split(","),
        exclude=args.exclude.split(","),
    )


if __name__ == "__main__":
    main()