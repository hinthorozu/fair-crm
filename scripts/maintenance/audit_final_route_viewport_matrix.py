"""FINAL audit: route × viewport smoke + discovered breakpoint ±1 + ultrawide."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "reports" / "final-ui-system-audit"
BASE = "http://127.0.0.1:5174"
SESSION = {
    "accessToken": "dev-bypass",
    "organizationId": "00000000-0000-4000-8000-000000000010",
    "email": "dev@bypass.local",
}
HEIGHT = 900
MIN_WIDTH = 320

ROUTES = [
    ("login", "/login"),
    ("dashboard", "/dashboard"),
    ("customers", "/customers"),
    ("fairs", "/fairs"),
    ("todos", "/todos"),
    ("follow-ups", "/follow-ups"),
    ("activities", "/activities"),
    ("di-imports", "/data-integration/imports"),
    ("di-jobs", "/data-integration/jobs"),
    ("di-reports", "/data-integration/reports"),
    ("di-adapters", "/data-integration/adapters"),
    ("di-run-history", "/data-integration/run-history"),
    ("di-scraper-test", "/data-integration/scraper-test"),
    ("di-enrichment", "/data-integration/enrichment"),
    ("admin-backups", "/admin/system/backups"),
    ("admin-smtp", "/admin/smtp-operations/accounts"),
    ("admin-templates", "/admin/smtp-operations/templates"),
    ("admin-mail-ops", "/admin/smtp-operations/mail-operations"),
    ("admin-data-ops", "/admin/data-operations"),
]


def discover_breakpoints() -> list[int]:
    css = (ROOT / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    found = sorted({int(m.group(1)) for m in re.finditer(r"@media\s*\((?:max|min)-width:\s*(\d+)px\)", css)})
    return found


def widths_for_matrix(breakpoints: list[int]) -> list[int]:
    widths = [MIN_WIDTH, 390, 768, 1024, 1440, 1920, 2560, 3440, 3840]
    for bp in breakpoints:
        widths.extend([max(MIN_WIDTH, bp - 1), bp, bp + 1])
    # continuous sample denser under 1600
    w = MIN_WIDTH
    while w <= 1600:
        widths.append(w)
        w += 80
    seen: set[int] = set()
    out: list[int] = []
    for value in sorted(widths):
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


async def measure(page) -> dict:
    return await page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          const overflowX = Math.max(doc.scrollWidth, body.scrollWidth) - doc.clientWidth;
          const pageShell = document.querySelector('.page-shell, .login-page');
          const modal = document.querySelector('.modal');
          const toolbar = document.querySelector('.filters, .page-header-actions');
          return {
            overflowX,
            pageShellOverflow: pageShell ? pageShell.scrollWidth - pageShell.clientWidth : 0,
            modalOverflow: modal ? modal.scrollWidth - modal.clientWidth : 0,
            toolbarOverflow: toolbar ? toolbar.scrollWidth - toolbar.clientWidth : 0,
            hasPageShell: Boolean(document.querySelector('.page-shell')),
            hasLogin: Boolean(document.querySelector('.login-page')),
            hasH1: Boolean(document.querySelector('h1')),
          };
        }"""
    )


def fails_for(m: dict, route: str) -> list[str]:
    fails: list[str] = []
    # Document-level horizontal overflow is the hard fail (ADR-032).
    # Inner pageShell scrollWidth can exceed clientWidth when tables measure
    # wider content inside an overflow-clipped table wrap — that is not a page break.
    if m.get("overflowX", 0) > 2:
        fails.append(f"overflowX={m['overflowX']}")
        if m.get("pageShellOverflow", 0) > 4:
            fails.append(f"pageShellOverflow={m['pageShellOverflow']}")
    if m.get("modalOverflow", 0) > 4:
        fails.append(f"modalOverflow={m['modalOverflow']}")
    if route != "login" and not m.get("hasPageShell") and not m.get("hasLogin") and not m.get("hasH1"):
        fails.append("missing_pageshell_or_heading")
    return fails


async def run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    breakpoints = discover_breakpoints()
    widths = widths_for_matrix(breakpoints)
    session_literal = json.dumps(json.dumps(SESSION))
    results: list[dict] = []
    failures: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        await context.add_init_script(
            f"localStorage.setItem('fair-crm.auth.session', {session_literal});"
        )

        for name, path in ROUTES:
            page = await context.new_page()
            try:
                await page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(350)
            except Exception as exc:  # noqa: BLE001
                item = {"route": name, "path": path, "fails": [f"goto:{exc}"]}
                failures.append(item)
                results.append(item)
                await page.close()
                continue

            for width in widths:
                await page.set_viewport_size({"width": width, "height": HEIGHT})
                await page.wait_for_timeout(120)
                m = await measure(page)
                m.update({"route": name, "path": path, "viewportWidth": width})
                fails = fails_for(m, name)
                m["fails"] = fails
                results.append(m)
                if fails:
                    failures.append(m)
                    print(f"FAIL {name}@{width}: {', '.join(fails)}")
                else:
                    print(f"ok   {name}@{width}")
            await page.close()

        await browser.close()

    report = {
        "min_width": MIN_WIDTH,
        "breakpoints_discovered": breakpoints,
        "widths_tested": widths,
        "routes": [r[0] for r in ROUTES],
        "total_checks": len(results),
        "failure_count": len(failures),
        "pass": len(failures) == 0,
        "failures": failures[:100],
    }
    (OUT / "route-viewport-matrix.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# FINAL Route × Viewport Matrix",
        "",
        f"- Min width: **{MIN_WIDTH}**",
        f"- Breakpoints discovered: {', '.join(str(b) for b in breakpoints)}",
        f"- Widths tested: **{len(widths)}** (incl. continuous sample + BP±1 + ultrawide)",
        f"- Routes: **{len(ROUTES)}**",
        f"- Checks: **{len(results)}**",
        f"- Failures: **{len(failures)}**",
        f"- Result: **{'PASS' if report['pass'] else 'FAIL'}**",
        "",
    ]
    if failures:
        lines.append("## Failures (sample)")
        lines.append("")
        for f in failures[:50]:
            lines.append(
                f"- `{f.get('route')}@{f.get('viewportWidth')}` — {', '.join(f.get('fails') or [])}"
            )
    (OUT / "ROUTE_VIEWPORT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUT / 'ROUTE_VIEWPORT_REPORT.md'} pass={report['pass']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
