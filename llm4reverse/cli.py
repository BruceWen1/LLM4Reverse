# -*- coding: utf-8 -*-
"""
cli.py
LLM4Reverse Command-Line Interface
=====================

This module defines the top-level CLI entrypoint. It dispatches to two subcommands:
- reverse: dynamic web reverse-engineering
- audit: static code audit
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Allow running as a script: `python llm4reverse/cli.py ...`
# When executed directly, Python's sys.path lacks the project root,
# so importing `llm4reverse.*` would fail. Add the parent directory.
if __package__ in (None, "") and str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from importlib.metadata import PackageNotFoundError, version

try:
    from llm4reverse import __version__
except ImportError:
    __version__ = None

from llm4reverse.reverse.pipeline import run_dynamic_reverse
from llm4reverse.audit.pipeline import run_static_audit

logger = logging.getLogger(__name__)


def configure_logging(verbose: bool) -> None:
    """
    Configure root logger format and level.

    Args:
        verbose (bool): If True, set DEBUG level; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
    )
    logger.debug("Logging configured, verbose=%s", verbose)


def build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI parser with subcommands.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(prog="llm4reverse", description="LLM4Reverse CLI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    
    # Prefer reading version from __init__.py, fallback to metadata if failed
    pkg_version = __version__
    if pkg_version is None:
        try:
            pkg_version = version("llm4reverse")
        except PackageNotFoundError:
            pkg_version = "0.0.0"
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"llm4reverse {pkg_version}",
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # reverse subcommand
    p_rev = subparsers.add_parser("reverse", help="Run dynamic web reverse workflow")
    p_rev.add_argument("--url", required=True, help="Target page URL to reverse")
    p_rev.add_argument("--output", "--outdir", default="./reverse_out", help="Output directory")
    p_rev.add_argument("--no-headless", action="store_true", help="Run browser in UI mode")
    p_rev.add_argument("--timeout", type=int, default=30, help="Extra wait after networkidle (seconds)")
    p_rev.set_defaults(func=handle_reverse)

    # audit subcommand
    p_aud = subparsers.add_parser("audit", help="Run static JS/TS code audit")
    p_aud.add_argument("--path", required=True, help="Path to local code directory")
    p_aud.add_argument(
        "--include",
        default=".js,.ts,.jsx,.tsx",
        help="Comma-separated glob patterns to include",
    )
    p_aud.add_argument(
        "--exclude",
        default="node_modules,dist,build,.git",
        help="Comma-separated directory names to exclude",
    )
    p_aud.set_defaults(func=handle_audit)

    return parser


def handle_reverse(args: argparse.Namespace) -> int:
    """
    Handle the 'reverse' subcommand.

    Args:
        args (argparse.Namespace): Parsed args with url, jsfile, model.

    Returns:
        int: Exit code.
    """
    configure_logging(args.verbose)
    start = time.time()
    try:
        # Determine output directory (default to ./reverse_out)
        out_dir = getattr(args, "output", "./reverse_out")
        headless = not getattr(args, "no_headless", False)
        timeout = getattr(args, "timeout", 30)
        run_dynamic_reverse(url=args.url, out_dir=out_dir, headless=headless, timeout=timeout)
        logger.info("Reverse workflow completed in %.2f seconds", time.time() - start)
        return 0
    except Exception:
        logger.exception("Reverse workflow failed")
        return 1


def handle_audit(args: argparse.Namespace) -> int:
    """
    Handle the 'audit' subcommand.

    Args:
        args (argparse.Namespace): Parsed args with path, include, exclude.

    Returns:
        int: Exit code.
    """
    configure_logging(args.verbose)
    start = time.time()
    try:
        run_static_audit(
            path=args.path,
            include=args.include.split(","),
            exclude=args.exclude.split(","),
        )
        logger.info("Audit workflow completed in %.2f seconds", time.time() - start)
        return 0
    except Exception:
        logger.exception("Audit workflow failed")
        return 1


def main() -> int:
    """
    Main entrypoint: parse args and dispatch.

    This function is the main entry point of the CLI, responsible for parsing
    command-line arguments and calling the corresponding handler functions.

    Returns:
        int: Exit code (0 for success, non-zero for failure).
    """
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
