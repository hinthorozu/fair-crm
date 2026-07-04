"""Tests for shared Playwright BrowserService."""

from unittest.mock import patch

import pytest

from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service
from app.modules.scraper.core.playwright_availability import PlaywrightBrowserNotInstalledError


def _browser_config_for_tests() -> BrowserConfig:
    """Use a system browser channel when Playwright bundles are not installed."""
    return BrowserConfig(headless=True, channel="msedge")


def test_browser_service_can_be_created():
    service = BrowserService()
    assert service.is_launched is False
    assert service.page is None


def test_create_browser_service_factory():
    config = BrowserConfig(headless=True, timeout_ms=5_000, user_agent="TestAgent/1.0")
    service = create_browser_service(config)
    assert service.config == config


@pytest.mark.asyncio
async def test_browser_service_launch_raises_when_playwright_browser_missing():
    service = BrowserService(BrowserConfig(headless=True))
    with patch(
        "app.modules.scraper.core.browser_service.ensure_playwright_browser_installed",
        side_effect=PlaywrightBrowserNotInstalledError(),
    ):
        with pytest.raises(PlaywrightBrowserNotInstalledError, match="python -m playwright install"):
            await service.launch()


@pytest.mark.asyncio
async def test_browser_service_launch_and_close():
    service = BrowserService(_browser_config_for_tests())
    await service.launch()
    assert service.is_launched is True
    await service.close()
    assert service.is_launched is False


@pytest.mark.asyncio
async def test_browser_service_opens_about_blank():
    async with BrowserService(_browser_config_for_tests()) as service:
        await service.new_page()
        await service.goto("about:blank")
        assert service.page is not None
        assert service.page.url == "about:blank"


@pytest.mark.asyncio
async def test_browser_service_reads_simple_html():
    html_doc = "data:text/html,<html><body><h1 id='title'>Hello Scraper</h1></body></html>"
    async with BrowserService(_browser_config_for_tests()) as service:
        await service.new_page()
        await service.goto(html_doc)
        await service.wait_for("#title")

        html = await service.html()
        text = await service.text("#title")

        assert "Hello Scraper" in html
        assert text == "Hello Scraper"
        assert await service.exists("#title") is True
        assert await service.exists("#missing") is False
