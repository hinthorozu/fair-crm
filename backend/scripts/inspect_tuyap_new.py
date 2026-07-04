"""Inspect TÜYAP New exhibitor list DOM selectors for adapter tuning."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter
from app.modules.scraper.core.browser_service import BrowserConfig, create_browser_service
from app.modules.scraper.types.scraper_context import ScraperContext


def _browser_config_for_inspection() -> BrowserConfig:
    settings = get_settings()
    config = BrowserConfig.from_settings(settings)
    channel = config.channel or "msedge"
    return BrowserConfig(
        headless=config.headless,
        timeout_ms=config.timeout_ms,
        user_agent=config.user_agent,
        channel=channel,
    )


def _print_group(group_name: str, group: dict) -> None:
    print(f"\n[{group_name}]")
    recommended = group.get("recommended")
    if recommended:
        print(f"  recommended: {recommended}")
    else:
        print("  recommended: (none)")

    for selector, result in group.get("selectors", {}).items():
        count = result.get("count", 0)
        samples = result.get("samples", [])
        marker = " *" if selector == recommended else ""
        print(f"  - {selector}{marker}")
        print(f"      count: {count}")
        if samples:
            print("      samples:")
            for sample in samples[:5]:
                print(f"        - {sample}")
        else:
            print("      samples: (none)")


def _print_constant_updates(report: dict) -> None:
    updates = report.get("constant_updates") or {}
    if not updates:
        print("\n[constant_updates]")
        print("  No adapter constant changes suggested.")
        return

    print("\n[constant_updates]")
    for constant_name, change in updates.items():
        print(f"  {constant_name}")
        print(f"    current:     {change['current']}")
        print(f"    recommended: {change['recommended']}")


async def _inspect(url: str) -> dict:
    browser = create_browser_service(_browser_config_for_inspection())
    adapter = TuyapNewAdapter(browser=browser)
    context = ScraperContext(list_url=url)

    async with browser:
        return adapter.inspect_selectors(context)


def main() -> None:
    if len(sys.argv) != 2:
        print('Usage: python backend/scripts/inspect_tuyap_new.py "<URL>"')
        raise SystemExit(1)

    url = sys.argv[1].strip()
    if not url:
        print("URL must not be empty.")
        raise SystemExit(1)

    report = asyncio.run(_inspect(url))

    print(f"URL: {report['url']}")
    for group_name, group in report.get("groups", {}).items():
        _print_group(group_name, group)
    _print_constant_updates(report)


if __name__ == "__main__":
    main()
