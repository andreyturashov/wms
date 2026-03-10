"""
Generic browser tool for AI agents.

Uses Playwright to open any URL in a headless Chromium browser, extract the
visible text, and return it for the LLM to reason over.  This allows agents to
answer questions that require live web data (e.g. ticket prices, schedules).

The tool is designed to be used inside a LangGraph / ReAct agent loop so the
LLM decides *when* and *what* to browse.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Maximum characters returned to the LLM to avoid blowing up context windows.
_MAX_CONTENT_LENGTH = 8000


@tool
async def browse_webpage(url: str) -> str:
    """Open a URL in a headless browser and return the visible text content.

    Use this tool when you need live information from a website — for example
    ticket prices, bus/train schedules, product pages, documentation, etc.
    Pass the full URL (including https://).  The tool returns the page's
    visible text (up to 8 000 characters).
    """
    from playwright.async_api import async_playwright

    logger.info("Browsing %s", url)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            # Give JS-rendered content a moment to settle
            await page.wait_for_timeout(2000)
            text = await page.inner_text("body")
            await browser.close()

            text = text.strip()
            if len(text) > _MAX_CONTENT_LENGTH:
                text = text[:_MAX_CONTENT_LENGTH] + "\n…(truncated)"
            return text
    except Exception as exc:
        logger.warning("browse_webpage failed for %s: %s", url, exc)
        return f"Error browsing {url}: {exc}"
