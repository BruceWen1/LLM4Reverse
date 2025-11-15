# -*- coding: utf-8 -*-
"""
browser.py
Reverse Module - Collectors
=====================

Playwright helper that records network traffic to HAR file.

Usage
-----
with BrowserSession(har_path="traffic.har") as page:
    page.goto("https://example.com", wait_until="networkidle")
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from playwright.sync_api import Page, Playwright, sync_playwright

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    Context manager wrapping Playwright to capture traffic as HAR.
    """

    def __init__(self, har_path: str, headless: bool = True) -> None:
        """
        Initialize browser session.

        Args:
            har_path (str): Path to save HAR file.
            headless (bool): Whether to run browser in headless mode.
        """
        self.har_path = Path(har_path).expanduser().resolve()
        self.headless = headless
        self._pw: Optional[Playwright] = None
        self.page: Optional[Page] = None

    # ------------------------------------------------------------------ #
    # Context-manager interface
    # ------------------------------------------------------------------ #
    def __enter__(self) -> Page:
        """
        Enter context manager, start browser and begin recording HAR.

        Returns:
            Page: Playwright page object.
        """
        self._pw = sync_playwright().start()
        browser = self._pw.chromium.launch(headless=self.headless)
        ctx = browser.new_context(record_har_path=str(self.har_path))
        self.page = ctx.new_page()
        logger.info("Browser started; HAR -> %s", self.har_path)
        return self.page

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        """
        Exit context manager, close browser and save HAR file.

        Args:
            exc_type: Exception type.
            exc: Exception instance.
            tb: Traceback object.
        """
        # HAR saved when context.close()
        # 安全关闭浏览器会话，处理可能的空值情况
        if self.page is not None:
            try:
                self.page.context.close()
            except Exception as e:
                logger.warning("Error closing page context: %s", e)
        
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception as e:
                logger.warning("Error stopping playwright: %s", e)
        
        logger.info("Browser closed; HAR saved.")


