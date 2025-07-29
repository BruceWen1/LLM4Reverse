# -*- coding: utf-8 -*-
"""
Command-line interface for LLM4Reverse.

This module defines a small CLI with two subcommands:
- reverse: run the reverse workflow
- playwright-install: install Playwright browsers

Expert-friendly design notes:
- Arguments map 1:1 to internal function parameters.
- Fails gracefully when optional deps (Playwright/Node) are missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

from .agent import ReverseAgent
from .report import save_artifacts
from .tools.browser import BrowserTool, PlaywrightNotAvailableError
from .tools.js_ast import try_extract_ast
from .tools.js_beautify import JSBeautifyTool


def _cmd_playwright_install(_: argparse.Namespace) -> int:
    """Install Playwright browsers via Python entry-point.

    Returns:
        int: Exit code (0 for success).
    """
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        print("Playwright browsers installed.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Playwright install failed: {e}", file=sys.stderr)
        return 1


def _cmd_reverse(args: argparse.Namespace) -> int:
    """Run the reverse workflow and save artifacts.

    Args:
        args: Parsed CLI arguments.

    Returns:
        int: Exit code.
    """
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Capture (optional)
    capture: Optional[Dict[str, Any]] = None
    if not args.no_browser:
        try:
            browser = BrowserTool(headless=not args.show_browser, timeout_ms=20000)
            capture = browser.capture(
                url=args.url,
                click_selector=args.click,
                wait_after_ms=args.wait_ms,
                include_dom=True,
            )
        except PlaywrightNotAvailableError as e:
            print(f"[warn] Browser capture disabled: {e}")
            capture = None

    # 2) JS beautify + 3) optional AST
    js_report: Optional[Dict[str, Any]] = None
    ast_report: Optional[Dict[str, Any]] = None

    if args.jsfile:
        js_path = Path(args.jsfile)
        if not js_path.exists():
            print(f"[error] JS file not found: {js_path}")
            return 2
        code = js_path.read_text(encoding="utf-8", errors="ignore")

        jsb = JSBeautifyTool()
        js_report = jsb.run(code)

        if args.ast:
            ast_report = try_extract_ast(code)

    # 4) LLM reasoning (optional)
    reverse_md: Optional[str] = None
    if not args.no_llm:
        agent = ReverseAgent(model=args.model, base_url=args.base_url)
        evidence = {
            "targetURL": args.url,
            "browserCapture": capture,
            "jsBeautify": js_report,
            "jsAST": ast_report,
        }
        reverse_md = agent.reason(evidence)

    # 5) Save
    save_artifacts(
        outdir=outdir,
        capture=capture,
        js_report=js_report,
        ast_report=ast_report,
        reverse_md=reverse_md,
    )

    if reverse_md:
        print(f"[ok] Reverse report written: {outdir / 'reverse_report.md'}")
    else:
        print(f"[ok] Evidence saved (no LLM report). Output: {outdir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="llm4reverse",
        description="Front-end reverse engineering with LLM-assisted tooling.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_rev = sub.add_parser("reverse", help="Run reverse workflow")
    p_rev.add_argument("--url", required=True, help="Target URL")
    p_rev.add_argument("--click", default=None, help="Optional CSS selector to click once")
    p_rev.add_argument("--wait-ms", type=int, default=2500, help="Wait after load/click (ms)")
    p_rev.add_argument("--jsfile", default=None, help="Optional local JS file")
    p_rev.add_argument("--ast", action="store_true", help="Enable AST (requires Node + esprima)")
    p_rev.add_argument("--no-browser", action="store_true", help="Disable headless capture")
    p_rev.add_argument("--show-browser", action="store_true", help="Run non-headless for debugging")
    p_rev.add_argument("--outdir", default="./artifacts", help="Output directory")
    p_rev.add_argument("--model", default=None, help="Override model (default from env)")
    p_rev.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL")
    p_rev.add_argument("--no-llm", action="store_true", help="Skip LLM; save evidence only")
    p_rev.set_defaults(func=_cmd_reverse)

    p_pw = sub.add_parser("playwright-install", help="Install Playwright browsers")
    p_pw.set_defaults(func=_cmd_playwright_install)

    return parser


def main() -> None:
    """Entry point for console script."""
    parser = build_parser()
    args = parser.parse_args()
    rc = args.func(args)
    raise SystemExit(rc)
