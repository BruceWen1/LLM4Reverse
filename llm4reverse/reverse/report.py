# -*- coding: utf-8 -*-
"""
report.py
Reverse Report
=====================

Write JSON + Markdown report after dynamic reverse-engineering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


def write_reverse_report(findings: List[Dict], out_dir: Path) -> None:
    """
    Save findings to disk.

    Args:
        findings (List[Dict]): Interface list.
        out_dir (Path): Output directory.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    findings_json = json.dumps(findings, ensure_ascii=False, indent=2)
    # Write to two filenames for compatibility (reverse_report.json for backward compatibility, reverse_findings.json for tests)
    (out_dir / "reverse_report.json").write_text(findings_json)
    (out_dir / "reverse_findings.json").write_text(findings_json)

    md_lines = ["# Dynamic Reverse Report\n"]
    for item in findings:
        md_lines.append(f"## `{item['method']}` {item['url']}")
        md_lines.append("")
        md_lines.append("```json")
        md_lines.append(json.dumps(item, ensure_ascii=False, indent=2))
        md_lines.append("```")
        md_lines.append("")

    (out_dir / "reverse_report.md").write_text("\n".join(md_lines))
