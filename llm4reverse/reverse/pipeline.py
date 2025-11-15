# -*- coding: utf-8 -*-
"""
pipeline.py
Reverse Module
=====================

Dynamic reverse-engineering workflow.

Steps
-----
1. Launch a headless (or headed) browser and record traffic as a HAR file.
2. Parse the HAR into a Python dict and let an LLM (ReAct chain) infer
   interface details such as headers / params / auth.
3. Write JSON / Markdown reports together with the full LLM trace.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple

from llm4reverse.reverse.collectors.browser import BrowserSession
from llm4reverse.reverse.agents.har_agent import run_har_agent
from llm4reverse.reverse import report as report_writer

logger = logging.getLogger(__name__)


def run_dynamic_reverse(url: str, out_dir: str, headless: bool = True, timeout: int = 30) -> None:
    """
    Capture runtime traffic (HAR) and let an LLM analyse it.

    Args:
        url (str): Target webpage URL.
        out_dir (str): Directory where artifacts will be stored.
        headless (bool): Launch browser in headless mode if True.
        timeout (int): Extra seconds to wait after 'networkidle'.
    """
    t0 = time.perf_counter()
    logger.info("Starting dynamic reverse engineering for: %s", url)
    
    # Prepare output directory
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    har_file = out / "traffic.har"
    logger.info("Output directory: %s", out)

    # Step 1: Record HAR via Playwright
    logger.info("Step 1/3: Starting browser session...")
    t1 = time.perf_counter()
    with BrowserSession(str(har_file), headless=headless) as page:
        try:
            logger.info("Navigating to %s (waiting for networkidle)...", url)
            page.goto(url, wait_until="networkidle")  # Prefer full quiet
        except Exception:
            logger.warning("Navigation with networkidle timed out; retrying with domcontentloaded")
            try:
                logger.info("Retrying navigation with domcontentloaded...")
                page.goto(url, wait_until="domcontentloaded")  # Weaker condition
            except Exception:
                logger.warning("Navigation failed; continuing to save whatever HAR is available")
        logger.info("Waiting additional %d seconds for page resources...", timeout)
        page.wait_for_timeout(timeout * 1000)  # Additional buffer

    logger.info("HAR captured -> %s (took %.2fs)", har_file, time.perf_counter() - t1)
    
    # 检查 HAR 文件是否有效
    if not har_file.exists():
        raise FileNotFoundError(f"HAR file was not created: {har_file}")
    
    har_size = har_file.stat().st_size / (1024 * 1024)  # Convert to MB
    logger.info("HAR file size: %.2f MB", har_size)
    
    # 如果 HAR 文件太小（小于 1KB），可能没有捕获到有效流量
    if har_size < 0.001:  # 小于 1KB
        logger.warning("HAR file is very small (%.2f KB), may not contain valid traffic", har_size * 1024)
    
    # 验证 HAR 文件是否为有效的 JSON，并加载数据供后续使用
    try:
        har_dict = json.loads(har_file.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(har_dict, dict) or "log" not in har_dict:
            logger.warning("HAR file structure may be invalid (missing 'log' key)")
    except json.JSONDecodeError as e:
        logger.error("HAR file is not valid JSON: %s", e)
        raise ValueError(f"Invalid HAR file format: {e}") from e

    # Step 2: LLM reasoning
    logger.info("Step 2/3: Starting LLM analysis (this may take several minutes)...")
    t2 = time.perf_counter()
    findings, trace = run_har_agent(har_dict)
    logger.info("LLM reasoning completed (took %.2fs)", time.perf_counter() - t2)
    
    (out / "reverse_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))
    logger.info("Trace saved: %d events recorded", len(trace))

    # Step 3: Persist reports
    logger.info("Step 3/3: Writing reports...")
    t3 = time.perf_counter()
    report_writer.write_reverse_report(findings, out)
    logger.info("Reports written (took %.2fs)", time.perf_counter() - t3)
    
    logger.info("Reverse finished in %.2fs (total)", time.perf_counter() - t0)


# --------------------------------------------------------------------------- #
# CLI helper
# --------------------------------------------------------------------------- #
def _parse() -> argparse.Namespace:
    """
    Define and parse CLI arguments.

    Returns:
        argparse.Namespace: Parsed CLI args.
    """
    p = argparse.ArgumentParser(description="Dynamic reverse-engineering (HAR + LLM).")
    p.add_argument("--url", required=True, help="Target page URL.")
    p.add_argument("--output", default="./reverse_out", help="Output directory.")
    p.add_argument("--no-headless", action="store_true", help="Run browser in UI mode.")
    p.add_argument("--timeout", type=int, default=30, help="Extra wait after networkidle (seconds).")
    return p.parse_args()


def main() -> None:
    """
    Entry point when executed as a script.

    This function configures logging, parses command-line arguments,
    and executes the dynamic reverse engineering workflow.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse()
    run_dynamic_reverse(args.url, args.output, not args.no_headless, args.timeout)


if __name__ == "__main__":
    main()
