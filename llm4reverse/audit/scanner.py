# -*- coding: utf-8 -*-
"""
scanner.py
Audit Module
=====================

Recursively scan a local code directory and yield source files matching include/exclude.
"""

import logging
from pathlib import Path
from typing import Iterable, Set

logger = logging.getLogger(__name__)


def iter_source_files(code_dir: str, include_exts: Set[str], exclude_dirs: Set[str]) -> Iterable[Path]:
    """
    Walk directory tree and yield source files.

    Args:
        code_dir (str): Root path of code directory.
        include_exts (Set[str]): File extensions to include, e.g. {'.js', '.ts'}.
        exclude_dirs (Set[str]): Directory names to skip entirely.

    Returns:
        Iterable[Path]: Paths to matching source files.
    """
    root = Path(code_dir)
    logger.info("Scanning directory: %s", root)
    # Recursively traverse directory tree
    for path in root.rglob("*"):
        # Skip excluded directories
        if any(part in exclude_dirs for part in path.parts):
            continue
        # Yield files with matching extensions
        if path.is_file() and path.suffix in include_exts:
            yield path
    logger.info("Directory scan complete")
