"""Shared Playwright browser lifecycle for all scraper adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class BrowserConfig:
    """Playwright browser settings for scraper runs."""

    headless: bool = True
    timeout_ms: int = 30_000
    user_agent: str = DEFAULT_USER_AGENT
    channel: str | None = None

    @classmethod
    def from_settings(cls, settings: Any) -> BrowserConfig:
        return cls(
            headless=settings.scraper_browser_headless,
            timeout_ms=settings.scraper_browser_timeout_ms,
            user_agent=settings.scraper_browser_user_agent,
            channel=settings.scraper_browser_channel,
        )


class BrowserService:
    """Central browser manager — adapters must not launch Playwright directly."""

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def config(self) -> BrowserConfig:
        return self._config

    @property
    def is_launched(self) -> bool:
        return self._browser is not None

    @property
    def page(self) -> Page | None:
        return self._page

    async def launch(self) -> None:
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        launch_options: dict[str, Any] = {"headless": self._config.headless}
        if self._config.channel:
            launch_options["channel"] = self._config.channel
        self._browser = await self._playwright.chromium.launch(**launch_options)
        self._context = await self._browser.new_context(user_agent=self._config.user_agent)

    async def close(self) -> None:
        if self._page is not None:
            await self._page.close()
            self._page = None
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def new_page(self) -> Page:
        self._ensure_launched()
        if self._page is not None:
            await self._page.close()
        assert self._context is not None
        page = await self._context.new_page()
        page.set_default_timeout(self._config.timeout_ms)
        self._page = page
        return page

    async def goto(self, url: str) -> None:
        page = self._require_page()
        await page.goto(url, timeout=self._config.timeout_ms)

    async def wait_for(self, selector: str) -> None:
        page = self._require_page()
        await page.wait_for_selector(selector, timeout=self._config.timeout_ms)

    async def html(self) -> str:
        page = self._require_page()
        return await page.content()

    async def screenshot(self, *, path: str | None = None) -> bytes:
        page = self._require_page()
        return await page.screenshot(path=path, type="png")

    async def evaluate(self, script: str) -> Any:
        page = self._require_page()
        return await page.evaluate(script)

    async def click(self, selector: str) -> None:
        page = self._require_page()
        await page.click(selector, timeout=self._config.timeout_ms)

    async def text(self, selector: str) -> str:
        page = self._require_page()
        return (await page.locator(selector).inner_text()).strip()

    async def exists(self, selector: str) -> bool:
        page = self._require_page()
        return await page.locator(selector).count() > 0

    async def query_count(self, selector: str) -> int:
        page = self._require_page()
        return await page.locator(selector).count()

    async def texts(self, selector: str, *, limit: int = 20) -> list[str]:
        page = self._require_page()
        locator = page.locator(selector)
        count = await locator.count()
        samples: list[str] = []
        for index in range(min(count, limit)):
            text = (await locator.nth(index).inner_text()).strip()
            if text:
                samples.append(text)
        return samples

    async def attrs(self, selector: str, attr: str, *, limit: int = 20) -> list[str]:
        page = self._require_page()
        locator = page.locator(selector)
        count = await locator.count()
        samples: list[str] = []
        for index in range(min(count, limit)):
            value = await locator.nth(index).get_attribute(attr)
            if value:
                samples.append(value.strip())
        return samples

    async def __aenter__(self) -> BrowserService:
        await self.launch()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    def _ensure_launched(self) -> None:
        if self._browser is None or self._context is None:
            raise RuntimeError("BrowserService.launch() must be called before using the browser")

    def _require_page(self) -> Page:
        self._ensure_launched()
        if self._page is None:
            raise RuntimeError("BrowserService.new_page() must be called before page interaction")
        return self._page


def create_browser_service(config: BrowserConfig | None = None) -> BrowserService:
    return BrowserService(config)
