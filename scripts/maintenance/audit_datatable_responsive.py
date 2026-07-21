"""Inventory all DataTable usages and smoke-test every list screen at ADR-032 viewports."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.async_api import Page, async_playwright

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
OUT = Path(__file__).resolve().parent / "reports" / "datatable-responsive-audit-20260721"
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

# Production table screens to smoke (path, slug, wait selector)
TABLE_SCREENS = [
    ("/dashboard", "dashboard", "h1"),
    ("/customers", "customers", "h1"),
    ("/fairs", "fairs", "h1"),
    ("/todos", "todos", "h1"),
    ("/follow-ups", "follow-ups", "h1"),
    ("/activities", "activities", "h1"),
    ("/data-integration/imports", "imports", "h1"),
    ("/data-integration/adapters", "adapters", "h1"),
    ("/data-integration/run-history", "run-history", "h1"),
    ("/admin/system/backups", "backups", "h1"),
    ("/admin/smtp-operations/accounts", "smtp-accounts", "h1"),
    ("/admin/smtp-operations/templates", "mail-templates", "h1"),
    ("/admin/smtp-operations/mail-operations", "mail-operations", "h1"),
    ("/admin/data-operations", "data-operations", "h1"),
]


@dataclass
class InventoryRow:
    file: str
    kind: str
    class_name: str | None
    notes: str


def inventory() -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    patterns = [
        (r"<UniversalDataTable\b", "UniversalDataTable"),
        (r"<WidthResponsiveDataTable\b", "WidthResponsiveDataTable"),
        (r"<ResponsiveDataTable\b", "ResponsiveDataTable"),
        (r"<DataTable\b", "DataTable"),
        (r"<DataTableShell\b", "DataTableShell"),
        (r"<table\b", "raw-html-table"),
    ]
    for path in FRONTEND_SRC.rglob("*.tsx"):
        rel = path.relative_to(ROOT).as_posix()
        if "node_modules" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, kind in patterns:
            for match in re.finditer(pattern, text):
                # Skip type-only / import-only false positives for DataTable word in comments
                line_start = text.rfind("\n", 0, match.start()) + 1
                line = text[line_start : text.find("\n", match.start())]
                if line.strip().startswith("//") or line.strip().startswith("*"):
                    continue
                if kind == "raw-html-table" and "UniversalDataTable" in text:
                    # Still record raw tables in files that also use Universal
                    pass
                class_name = None
                snippet = text[match.start() : match.start() + 400]
                cm = re.search(r'className=["\']([^"\']+)["\']', snippet)
                if cm:
                    class_name = cm.group(1)
                notes = ""
                if kind == "DataTableShell":
                    notes = "specialty shell (scroll-only allowed for Import Wizard)"
                if kind == "raw-html-table" and "excel-mapping" in rel:
                    notes = "ADR-032 specialty spreadsheet grid (scroll-only)"
                if kind == "DataTable" and "components/ui/DataTable.tsx" in rel:
                    continue  # definition
                if kind == "WidthResponsiveDataTable" and "WidthResponsiveDataTable.tsx" in rel:
                    continue
                rows.append(InventoryRow(file=rel, kind=kind, class_name=class_name, notes=notes))
    return rows


async def measure(page: Page) -> dict:
    return await page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          const roots = [...document.querySelectorAll('.width-responsive-table-root')];
          const wraps = [...document.querySelectorAll('.table-wrap--width-responsive')];
          const liveTables = [...document.querySelectorAll(
            '.table-wrap--width-responsive > .data-table, .table-wrap--width-responsive table.data-table'
          )].filter((t) => !t.closest('.width-responsive-measure'));
          const pageOverflow = Math.max(doc.scrollWidth, body.scrollWidth) - doc.clientWidth;
          const tableIssues = liveTables.map((t) => {
            const wrap = t.closest('.table-wrap') || t.parentElement;
            const root = t.closest('.width-responsive-table-root');
            return {
              tableScroll: t.scrollWidth,
              tableClient: t.clientWidth,
              wrapClient: wrap ? wrap.clientWidth : null,
              rootClient: root ? root.clientWidth : null,
              overflow: t.scrollWidth - (wrap ? wrap.clientWidth : t.clientWidth),
            };
          });
          const maxTableOverflow = tableIssues.reduce((m, i) => Math.max(m, i.overflow || 0), 0);
          const hasWidthResponsive = wraps.length > 0 || roots.length > 0;
          const hasLegacyScrollWrap = !!document.querySelector(
            '.table-wrap:not(.table-wrap--width-responsive):not(.table-wrap--scroll-only):not(.table-skeleton-wrap)'
          );
          return {
            viewportWidth: window.innerWidth,
            pageOverflowX: pageOverflow,
            widthResponsiveCount: wraps.length,
            maxTableOverflow,
            hasWidthResponsive,
            hasLegacyScrollWrap,
            tableIssues,
          };
        }"""
    )


async def shot(page: Page, name: str) -> None:
    path = OUT / "screenshots" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=False)


async def resolve_dynamic_paths(page: Page) -> list[tuple[str, str, str]]:
    extras: list[tuple[str, str, str]] = []
    # First customer
    await page.goto(f"{BASE}/customers", wait_until="networkidle", timeout=90000)
    href = await page.locator("a[href^='/customers/']").first.get_attribute("href")
    if href:
        extras.append((href, "customer-detail", "h1"))
    # First fair
    await page.goto(f"{BASE}/fairs", wait_until="networkidle", timeout=90000)
    href = await page.locator("a[href^='/fairs/']").first.get_attribute("href")
    if href:
        extras.append((href, "fair-detail", "h1"))
    # First adapter
    await page.goto(f"{BASE}/data-integration/adapters", wait_until="networkidle", timeout=90000)
    href = await page.locator("a[href*='/data-integration/adapters/']").first.get_attribute("href")
    if href and href.rstrip("/") != "/data-integration/adapters":
        extras.append((href, "adapter-detail", "h1"))
    # Duplicate analysis run if available
    await page.goto(f"{BASE}/admin/data-operations", wait_until="networkidle", timeout=90000)
    href = await page.locator("a[href*='/admin/data-operations/runs/']").first.get_attribute("href")
    if href:
        extras.append((href, "duplicate-or-analyze-run", "h1"))
    else:
        card = page.locator(".data-operation-card", has_text="Duplicate").first
        if await card.count() > 0:
            btn = card.locator("button").last
            await btn.click()
            try:
                await page.wait_for_url("**/admin/data-operations/runs/**", timeout=60000)
                extras.append((page.url.replace(BASE, ""), "duplicate-or-analyze-run", "h1"))
            except Exception:
                pass
    return extras


async def smoke_screen(page: Page, path: str, slug: str) -> list[dict]:
    results: list[dict] = []
    await page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=90000)
    try:
        await page.wait_for_selector("h1, .page, .admin-content, .di-content", timeout=30000)
    except Exception:
        pass
    await page.wait_for_timeout(700)

    for label, width, height in VIEWPORTS:
        await page.set_viewport_size({"width": width, "height": height})
        await page.wait_for_timeout(1200)
        await page.evaluate("() => document.body.offsetHeight")
        try:
            await page.locator("h1").first.click(force=True)
        except Exception:
            pass
        await page.wait_for_timeout(150)
        m = await measure(page)
        # PASS: page must not overflow; WR tables must not exceed wrap (border-box slack ≤16).
        page_ok = (m.get("pageOverflowX") or 0) <= 2
        table_ok = True
        if m.get("hasWidthResponsive"):
            table_ok = (m.get("maxTableOverflow") or 0) <= 16
        status = "PASS" if page_ok and table_ok else "FAIL"
        reasons = []
        if not page_ok:
            reasons.append(f"pageOverflowX={m.get('pageOverflowX')}")
        if not table_ok:
            reasons.append(f"maxTableOverflow={m.get('maxTableOverflow')}")
        row = {
            "slug": slug,
            "path": path,
            "viewport": label,
            "status": status,
            "reasons": reasons,
            **m,
        }
        results.append(row)
        await shot(page, f"{slug}-{label}-{status}.png")
        if label == "390x844" and m.get("hasWidthResponsive"):
            expand = page.locator(
                "button[aria-label*='genişlet'], button[aria-label*='Expand'], "
                "button[aria-label*='expand']"
            ).first
            if await expand.count() > 0:
                await expand.click(force=True)
                await page.wait_for_timeout(400)
                await shot(page, f"{slug}-390x844-child-open.png")
    return results


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inv = inventory()
    (OUT / "inventory.json").write_text(
        json.dumps([asdict(r) for r in inv], indent=2), encoding="utf-8"
    )

    # Summary inventory markdown
    by_kind: dict[str, int] = {}
    for r in inv:
        by_kind[r.kind] = by_kind.get(r.kind, 0) + 1

    session_literal = json.dumps(json.dumps(SESSION))
    all_results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        await context.add_init_script(
            f"localStorage.setItem('fair-crm.auth.session', {session_literal});"
        )
        page = await context.new_page()

        screens = list(TABLE_SCREENS)
        try:
            screens.extend(await resolve_dynamic_paths(page))
        except Exception as exc:
            print(f"WARN dynamic paths: {exc}")

        seen: set[str] = set()
        for path, slug, _wait in screens:
            if slug in seen:
                continue
            seen.add(slug)
            print(f"smoke {slug} ({path})")
            try:
                all_results.extend(await smoke_screen(page, path, slug))
            except Exception as exc:
                all_results.append(
                    {
                        "slug": slug,
                        "path": path,
                        "viewport": "n/a",
                        "status": "FAIL",
                        "reasons": [str(exc)],
                    }
                )
                print(f"  FAIL: {exc}")

        await browser.close()

    (OUT / "smoke-results.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")

    # PASS/FAIL report
    lines = [
        "# DataTable Responsive Audit",
        "",
        "## Inventory counts",
        "",
    ]
    for kind, count in sorted(by_kind.items()):
        lines.append(f"- `{kind}`: {count}")
    lines += ["", "## Smoke results (390 / 768 / 1024 / 1440)", ""]
    lines.append("| Screen | 390 | 768 | 1024 | 1440 | Overall |")
    lines.append("|---|---|---|---|---|---|")

    by_slug: dict[str, list[dict]] = {}
    for r in all_results:
        by_slug.setdefault(r["slug"], []).append(r)

    overall_fail = 0
    for slug, rows in sorted(by_slug.items()):
        statuses = {r["viewport"]: r["status"] for r in rows if r.get("viewport") != "n/a"}
        overall = (
            "PASS"
            if rows and all(r["status"] == "PASS" for r in rows)
            else "FAIL"
        )
        if overall == "FAIL":
            overall_fail += 1
        lines.append(
            "| {slug} | {a} | {b} | {c} | {d} | **{o}** |".format(
                slug=slug,
                a=statuses.get("390x844", "—"),
                b=statuses.get("768x1024", "—"),
                c=statuses.get("1024x768", "—"),
                d=statuses.get("1440x900", "—"),
                o=overall,
            )
        )

    fails = [r for r in all_results if r["status"] == "FAIL"]
    lines += ["", f"**Screens failed:** {overall_fail} / {len(by_slug)}", ""]
    if fails:
        lines += ["## Failures", ""]
        for r in fails:
            lines.append(
                f"- `{r['slug']}` @ `{r.get('viewport')}`: {', '.join(r.get('reasons') or [])}"
            )

    report = "\n".join(lines) + "\n"
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)
    if overall_fail:
        raise SystemExit(1)
    print(f"All screens PASS. Artifacts: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
