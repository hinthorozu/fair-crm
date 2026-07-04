"""Tests for BrowserService DOM probe helpers."""

import pytest

from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService


def _browser_config_for_tests() -> BrowserConfig:
    return BrowserConfig(headless=True, channel="msedge")


@pytest.mark.asyncio
async def test_browser_service_query_count_texts_and_attrs():
    html_doc = (
        "data:text/html,<html><body>"
        "<div class='card'><h2 class='name'>Alpha Co</h2>"
        "<a class='site' href='https://alpha.test'>Site</a></div>"
        "<div class='card'><h2 class='name'>Beta Co</h2>"
        "<a class='site' href='https://beta.test'>Site</a></div>"
        "</body></html>"
    )
    async with BrowserService(_browser_config_for_tests()) as browser:
        await browser.new_page()
        await browser.goto(html_doc)

        assert await browser.query_count(".card") == 2
        assert await browser.query_count(".missing") == 0
        assert await browser.texts(".name", limit=5) == ["Alpha Co", "Beta Co"]
        assert await browser.attrs(".site", "href", limit=5) == [
            "https://alpha.test",
            "https://beta.test",
        ]
