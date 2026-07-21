"""Capture Activities central screen acceptance screenshots (local dev)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parent / "reports" / "activities-central-screen"
BASE = "http://127.0.0.1:5173"
SESSION = {
    "accessToken": "dev-bypass",
    "organizationId": "00000000-0000-4000-8000-000000000010",
    "email": "dev@bypass.local",
}


async def shot(page, name: str) -> None:
    path = OUT / name
    await page.screenshot(path=str(path))
    print(f"wrote {path.name} ({path.stat().st_size} bytes)")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    session_literal = json.dumps(json.dumps(SESSION))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        await context.add_init_script(
            f"localStorage.setItem('fair-crm.auth.session', {session_literal});"
        )
        page = await context.new_page()
        await page.goto(f"{BASE}/activities", wait_until="networkidle", timeout=90000)
        await page.reload(wait_until="networkidle")
        await page.wait_for_selector("text=Aktiviteler", timeout=30000)
        await page.wait_for_selector("button.btn.link.danger", state="attached", timeout=30000)
        await page.wait_for_timeout(800)
        await shot(page, "01-activities-wide.png")

        await page.set_viewport_size({"width": 900, "height": 900})
        await page.wait_for_timeout(900)
        await shot(page, "02-activities-medium.png")

        await page.set_viewport_size({"width": 390, "height": 900})
        await page.wait_for_timeout(1100)
        # Close any open user menu by clicking page title
        await page.locator("h1").first.click(force=True)
        await page.wait_for_timeout(200)
        await shot(page, "03-activities-narrow-closed.png")

        expand = page.locator("button[aria-label*='genişlet'], button[aria-label*='Expand']").first
        if await expand.count() == 0:
            expand = page.locator("tbody tr td:first-child button").first
        if await expand.count() > 0:
            await expand.click(force=True)
            await page.wait_for_timeout(600)
        await shot(page, "04-activities-narrow-child-open.png")

        await page.set_viewport_size({"width": 1440, "height": 900})
        await page.wait_for_timeout(800)
        status = page.locator('select[aria-label="Durum"]')
        await status.select_option(value="completed")
        await page.wait_for_timeout(1500)
        await shot(page, "05-activities-filtered.png")

        # Reset filter for interactive actions on a clean wide layout
        await status.select_option(value="")
        await page.wait_for_timeout(1200)
        await page.goto(f"{BASE}/activities", wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(1000)
        live = page.locator(".table-wrap--width-responsive")

        await live.locator("button.btn.link", has_text="Görüntüle").first.click()
        await page.wait_for_selector(".modal .detail-grid", timeout=10000)
        await page.wait_for_timeout(500)
        await shot(page, "06-activity-detail-modal.png")
        await page.locator(".modal-close, .modal-header button").first.click()
        await page.wait_for_timeout(400)

        await live.locator("button.btn.link.danger").first.click()
        await page.wait_for_timeout(500)
        await shot(page, "07-single-delete-confirm.png")
        await page.locator(".modal button", has_text="İptal").first.click()
        await page.wait_for_timeout(300)

        checks = live.locator('tbody input[type="checkbox"]')
        for i in range(min(await checks.count(), 2)):
            await checks.nth(i).check()
        await page.wait_for_timeout(300)
        await page.locator("button", has_text="Seçilenleri Sil").first.click()
        await page.wait_for_timeout(500)
        await shot(page, "08-bulk-delete-confirm.png")
        await page.locator(".modal button", has_text="İptal").first.click()
        await page.wait_for_timeout(300)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(600)
        await shot(page, "09-bottom-pagination.png")

        await browser.close()

    print("all screenshots:")
    for path in sorted(OUT.glob("*.png")):
        print(f"  {path.name}\t{path.stat().st_size}")


if __name__ == "__main__":
    asyncio.run(main())
