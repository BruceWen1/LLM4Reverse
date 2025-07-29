# -*- coding: utf-8 -*-
"""
Headless browser capture powered by Playwright (optional).

- Navigate to a page
- Optionally click a selector
- Wait for a short period
- Collect network requests (method, URL, best-effort status, small postData snippet)
- Collect console logs
- Save a DOM snippet (prettified, trimmed)

If Playwright import fails, a specialized error is raised so callers can proceed without capture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from playwright.sync_api import sync_playwright
except Exception:  # noqa: BLE001
    sync_playwright = None  # type: ignore


class PlaywrightNotAvailableError(RuntimeError):
    """Raised when Playwright is not available but capture is requested."""


class BrowserTool:
    """Minimal wrapper around Playwright sync API for single-page capture."""

    def __init__(self, headless: bool = True, timeout_ms: int = 20000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        if sync_playwright is None:
            raise PlaywrightNotAvailableError(
                "Playwright not available. Install with `pip install -r requirements.txt` "
                "and run `llm4reverse playwright-install` to install browsers."
            )

    def capture(
        self,
        url: str,
        click_selector: Optional[str] = None,
        wait_after_ms: int = 2000,
        include_dom: bool = True,
    ) -> Dict[str, Any]:
        """Capture network/console/DOM for a single page visit."""
        from bs4 import BeautifulSoup  # local import

        with sync_playwright() as p:  # type: ignore[misc]
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            requests: List[Dict[str, Any]] = []
            console_logs: List[str] = []

            def on_request(req) -> None:
                entry = {"method": req.method, "url": req.url}
                post_data = req.post_data
                if post_data:
                    entry["postDataSnippet"] = post_data[:200]
                requests.append(entry)

            def on_response(res) -> None:
                try:
                    req_url = res.url
                    status = res.status
                    for i in range(len(requests) - 1, -1, -1):
                        if requests[i]["url"] == req_url and "status" not in requests[i]:
                            requests[i]["status"] = status
                            break
                except Exception:
                    pass

            def on_console(msg) -> None:
                console_logs.append(f"[{msg.type}] {msg.text}")

            page.on("request", on_request)
            page.on("response", on_response)
            page.on("console", on_console)

            page.goto(url, timeout=self.timeout_ms)

            if click_selector:
                try:
                    page.click(click_selector, timeout=self.timeout_ms)
                except Exception as e:
                    console_logs.append(f"[warn] click failed: {e!s}")

            page.wait_for_timeout(wait_after_ms)

            html = page.content() if include_dom else ""
            browser.close()

        dom_snippet = ""
        if html and include_dom:
            soup = BeautifulSoup(html, "html.parser")
            dom_snippet = soup.prettify()[:5000]

        return {"url": url, "requests": requests, "console": console_logs, "domSnippet": dom_snippet}
