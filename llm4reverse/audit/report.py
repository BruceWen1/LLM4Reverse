# -*- coding: utf-8 -*-
"""
report.py
Audit Module Report
=====================

Generate audit results as both JSON and well-formatted Markdown.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from llm4reverse.audit.extractors.regex_extractor import Finding

logger = logging.getLogger(__name__)


def _is_static_resource(url: str) -> bool:
    """
    Check whether the given URL likely points to a static resource.

    Args:
        url (str): The endpoint URL.

    Returns:
        bool: True if the URL is a static asset, False otherwise.
    """
    # 处理 None 或空字符串的情况
    if not url:
        return False
    static_exts = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".css", ".svg", ".woff", ".ttf", ".webp")
    return url.lower().endswith(static_exts)


def write_audit_report(findings: List[Finding], out_dir: Path) -> None:
    """
    Write static audit results to both JSON and Markdown files.

    Args:
        findings (List[Finding]): List of audit findings, potentially enriched by LLM.
        out_dir (Path): Output directory where reports will be written.
    """
    # Ensure output directory exists
    out = out_dir if isinstance(out_dir, Path) else Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Serialize findings for JSON
    findings_dict: List[Dict[str, Any]] = [f.__dict__ for f in findings]
    result: Dict[str, Any] = {"findings": findings_dict}

    # Generate JSON report
    json_path = out / "static_findings.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote JSON report to %s", json_path)

    # Generate Markdown report
    md_lines: List[str] = ["# Static Audit Report", ""]

    # Iterate over each finding and generate Markdown content
    for f in findings_dict:
        # 获取 URL，如果是 None 则使用空字符串
        url = f.get("url") or ""
        type_label = f.get("type", "unknown")
        method = f.get("method", "N/A")
        # 确保 confidence 是数字类型，如果是字符串则转换为浮点数
        confidence_raw = f.get("confidence", 0.0)
        if isinstance(confidence_raw, str):
            try:
                confidence = float(confidence_raw)
            except (ValueError, TypeError):
                confidence = 0.0
        else:
            confidence = float(confidence_raw) if confidence_raw is not None else 0.0

        # Skip or tag static resources
        if url and _is_static_resource(url):
            title = f"### [STATIC] {type_label} {url}"
        else:
            title = f"### {type_label.upper()} {url}"

        # Build Markdown section
        md_lines += [
            title,
            f"- **File**: `{f.get('file','')}:{f.get('line',0)}`",
            f"- **Method**: `{method}`",
            f"- **Confidence**: `{confidence:.2f}`",
        ]

        # Display optional fields
        headers = f.get("headers")
        params = f.get("params")
        body = f.get("body")

        if headers:
            md_lines += ["- **Headers**:", "```json", json.dumps(headers, ensure_ascii=False, indent=2), "```"]
        if params:
            md_lines += ["- **Params**:", "```json", json.dumps(params, ensure_ascii=False, indent=2), "```"]
        if body:
            md_lines += ["- **Body**:", "```json", json.dumps(body, ensure_ascii=False, indent=2), "```"]

        # Always include code snippet
        snippet = f.get("snippet", "")
        md_lines += ["- **Code Snippet**:", "```js", snippet, "```", ""]

    md_path = out / "static_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Wrote Markdown report to %s", md_path)
