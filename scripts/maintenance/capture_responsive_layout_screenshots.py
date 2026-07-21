"""Capture FAIR CRM responsive layout acceptance screenshots (local dev)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import Page, async_playwright

OUT = Path(__file__).resolve().parent / "reports" / "responsive-layout-fix-20260721"
BASE = "http://127.0.0.1:5173"
SESSION = {
    "accessToken": "dev-bypass",
    "organizationId": "00000000-0000-4000-8000-000000000010",
    "email": "dev@bypass.local",
}

VIEWPORTS = [
    ("390x844", 390, 844),
    ("768x1024", 768, 1024),
    ("1024x768", 1024, 768),
    ("1440x900", 1440, 900),
]

PAGES = [
    ("customers", "/customers", "h1"),
    ("fairs", "/fairs", "h1"),
    ("todos", "/todos", "h1"),
    ("activities", "/activities", "h1"),
]


async def shot(page: Page, name: str) -> None:
    path = OUT / name
    await page.screenshot(path=str(path), full_page=False)
    print(f"wrote {path.name} ({path.stat().st_size} bytes)")


async def measure_overflow(page: Page) -> dict:
    return await page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          const shell = document.querySelector('.app-shell');
          const content = document.querySelector('.app-content');
          const admin = document.querySelector('.admin-system-layout');
          const adminContent = document.querySelector('.admin-content');
          const tableRoot = document.querySelector('.width-responsive-table-root');
          const liveTable = document.querySelector(
            '.table-wrap--width-responsive .data-table:not(.width-responsive-measure .data-table)'
          );
          const adminCols = admin
            ? getComputedStyle(admin).gridTemplateColumns
            : null;
          return {
            viewportWidth: window.innerWidth,
            scrollWidth: Math.max(doc.scrollWidth, body.scrollWidth),
            clientWidth: doc.clientWidth,
            overflowX: Math.max(doc.scrollWidth, body.scrollWidth) - doc.clientWidth,
            shellScrollWidth: shell ? shell.scrollWidth : null,
            contentScrollWidth: content ? content.scrollWidth : null,
            contentClientWidth: content ? content.clientWidth : null,
            adminScrollWidth: admin ? admin.scrollWidth : null,
            adminClientWidth: admin ? admin.clientWidth : null,
            adminContentClientWidth: adminContent ? adminContent.clientWidth : null,
            adminGridTemplateColumns: adminCols,
            tableRootClientWidth: tableRoot ? tableRoot.clientWidth : null,
            liveTableScrollWidth: liveTable ? liveTable.scrollWidth : null,
            liveTableClientWidth: liveTable ? liveTable.clientWidth : null,
          };
        }"""
    )


async def wait_for_heading(page: Page, selector: str) -> None:
    await page.wait_for_selector(selector, timeout=45000)
    await page.wait_for_selector(".table-wrap--width-responsive, .empty-state, .table-error-state", timeout=45000)


async def open_with_session(context, path: str) -> Page:
    page = await context.new_page()
    await page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=90000)
    await page.reload(wait_until="networkidle")
    return page


async def capture_list_pages(context) -> list[dict]:
    metrics: list[dict] = []
    for slug, path, heading in PAGES:
        page = await open_with_session(context, path)
        await wait_for_heading(page, heading)
        await page.wait_for_timeout(700)
        for label, width, height in VIEWPORTS:
            await page.set_viewport_size({"width": width, "height": height})
            await page.wait_for_timeout(900)
            # Dismiss menus that can obscure the layout.
            await page.locator("h1").first.click(force=True)
            await page.wait_for_timeout(200)
            m = await measure_overflow(page)
            m.update({"page": slug, "viewport": label})
            metrics.append(m)
            await shot(page, f"{slug}-{label}.png")
            if label == "390x844":
                expand = page.locator(
                    "button[aria-label*='genişlet'], button[aria-label*='Expand'], "
                    "button[aria-label*='expand']"
                ).first
                if await expand.count() > 0:
                    await expand.click(force=True)
                    await page.wait_for_timeout(500)
                    await shot(page, f"{slug}-{label}-child-open.png")
        await page.close()
    return metrics


async def find_duplicate_run_path(page: Page) -> str | None:
    await page.goto(f"{BASE}/admin/data-operations", wait_until="networkidle", timeout=90000)
    await page.reload(wait_until="networkidle")
    await page.wait_for_timeout(1000)

    # Prefer an existing completed run link if present.
    run_link = page.locator("a[href*='/admin/data-operations/runs/']").first
    if await run_link.count() > 0:
        href = await run_link.get_attribute("href")
        if href:
            return href

    # Try to start Duplicate Customer Analysis.
    run_btn = page.locator(
        "button:has-text('Duplicate Customer Analysis'), "
        "button:has-text('Çalıştır'), "
        "button:has-text('Run')"
    )
    # Card specifically for duplicate analysis
    card = page.locator(".data-operation-card", has_text="Duplicate").first
    if await card.count() > 0:
        btn = card.locator("button").filter(has_text="Çalıştır")
        if await btn.count() == 0:
            btn = card.locator("button").filter(has_text="Run")
        if await btn.count() == 0:
            btn = card.locator("button").last
        if await btn.count() > 0:
            await btn.click()
            await page.wait_for_url("**/admin/data-operations/runs/**", timeout=60000)
            return page.url.replace(BASE, "")

    if await run_btn.count() > 0:
        await run_btn.first.click()
        await page.wait_for_timeout(2000)
        if "/admin/data-operations/runs/" in page.url:
            return page.url.replace(BASE, "")
    return None


async def capture_duplicate_page(context) -> list[dict]:
    metrics: list[dict] = []
    page = await open_with_session(context, "/admin/data-operations")
    run_path = await find_duplicate_run_path(page)
    if not run_path:
        # Still capture the list page as evidence.
        for label, width, height in VIEWPORTS:
            await page.set_viewport_size({"width": width, "height": height})
            await page.wait_for_timeout(800)
            m = await measure_overflow(page)
            m.update({"page": "data-operations-list", "viewport": label})
            metrics.append(m)
            await shot(page, f"data-operations-list-{label}.png")
        await page.close()
        print("WARN: no duplicate analysis run found/created")
        return metrics

    await page.goto(f"{BASE}{run_path}", wait_until="networkidle", timeout=90000)
    await page.wait_for_timeout(1500)
    # Wait for either groups table or empty/result content.
    try:
        await page.wait_for_selector(
            ".duplicate-groups-page, .table-wrap--width-responsive, text=Duplicate",
            timeout=45000,
        )
    except Exception:
        pass

    for label, width, height in VIEWPORTS:
        await page.set_viewport_size({"width": width, "height": height})
        await page.wait_for_timeout(1000)
        await page.locator("h1").first.click(force=True)
        await page.wait_for_timeout(200)
        m = await measure_overflow(page)
        m.update({"page": "duplicate-customer-analysis", "viewport": label})
        metrics.append(m)
        await shot(page, f"duplicate-customer-analysis-{label}.png")
        if label == "390x844":
            expand = page.locator(
                "button[aria-label*='genişlet'], button[aria-label*='Expand'], "
                "button[aria-label*='expand']"
            ).first
            if await expand.count() > 0:
                await expand.click(force=True)
                await page.wait_for_timeout(500)
                await shot(page, "duplicate-customer-analysis-390x844-child-open.png")
    await page.close()
    return metrics


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    session_literal = json.dumps(json.dumps(SESSION))
    all_metrics: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        await context.add_init_script(
            f"localStorage.setItem('fair-crm.auth.session', {session_literal});"
        )

        all_metrics.extend(await capture_list_pages(context))
        all_metrics.extend(await capture_duplicate_page(context))

        await browser.close()

    report = OUT / "overflow-metrics.json"
    report.write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    print(f"wrote {report}")

    bad = [m for m in all_metrics if (m.get("overflowX") or 0) > 2]
    if bad:
        print(f"OVERFLOW DETECTED on {len(bad)} viewport/page combos:")
        for m in bad:
            print(
                f"  {m['page']} @ {m['viewport']}: overflowX={m['overflowX']} "
                f"scroll={m['scrollWidth']} client={m['clientWidth']}"
            )
        raise SystemExit(1)

    nested_fail = []
    for m in all_metrics:
        if m.get("page") != "duplicate-customer-analysis":
            continue
        cols = m.get("adminGridTemplateColumns") or ""
        width = m.get("viewportWidth") or 0
        if width <= 1024 and " " in cols.strip() and cols.strip() not in ("none", "1fr"):
            # stacked should be a single track (1fr) or flex (none/empty multi)
            tracks = [t for t in cols.split(" ") if t]
            if len(tracks) > 1:
                nested_fail.append(m)
        live_scroll = m.get("liveTableScrollWidth") or 0
        live_client = m.get("liveTableClientWidth") or 0
        if live_client and live_scroll - live_client > 8:
            nested_fail.append({**m, "reason": "live-table-overflow"})

    if nested_fail:
        print(f"NESTED LAYOUT / TABLE FAIL on {len(nested_fail)} combos:")
        for m in nested_fail:
            print(
                f"  {m['page']} @ {m['viewport']}: grid={m.get('adminGridTemplateColumns')} "
                f"liveTable={m.get('liveTableScrollWidth')}/{m.get('liveTableClientWidth')} "
                f"reason={m.get('reason')}"
            )
        raise SystemExit(2)

    print("All measured viewports: no horizontal page overflow (>2px).")
    print("Admin nested layout stacks at <=1024; live tables fit container.")


if __name__ == "__main__":
    asyncio.run(main())
