import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import asyncio

from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService


async def main() -> None:
    browser = BrowserService(BrowserConfig(headless=True, channel="msedge"))
    async with browser:
        await browser.new_page()
        await browser.goto("https://www.foodistexpo.com/katilimci-listesi")
        print("ok", len(await browser.html()))


asyncio.run(main())
