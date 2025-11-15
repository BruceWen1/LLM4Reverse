# -*- coding: utf-8 -*-
"""
report.py
Artifact Saving Utilities
=====================

Centralizes how outputs are written to disk so that CLI remains concise.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def save_artifacts(
    outdir: Path,
    capture: Optional[Dict[str, Any]],
    js_report: Optional[Dict[str, Any]],
    ast_report: Optional[Dict[str, Any]],
    reverse_md: Optional[str],
) -> None:
    """
    Save all generated artifacts to the specified directory.

    Args:
        outdir (Path): Output directory path.
        capture (Optional[Dict[str, Any]]): Captured data dictionary.
        js_report (Optional[Dict[str, Any]]): JavaScript beautification report.
        ast_report (Optional[Dict[str, Any]]): AST analysis report.
        reverse_md (Optional[str]): Reverse engineering Markdown report.
    """
    # Create output directory if it doesn't exist
    outdir.mkdir(parents=True, exist_ok=True)

    # Save captured data
    if capture is not None:
        (outdir / "capture.json").write_text(json.dumps(capture, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save JavaScript beautification report
    if js_report is not None:
        (outdir / "js_beautify.json").write_text(json.dumps(js_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save AST analysis report
    if ast_report is not None:
        (outdir / "js_ast.json").write_text(json.dumps(ast_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save Markdown report
    if reverse_md:
        (outdir / "reverse_report.md").write_text(reverse_md, encoding="utf-8")
