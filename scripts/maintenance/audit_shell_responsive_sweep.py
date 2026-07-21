"""Continuous viewport sweep for FAIR CRM shell/chrome (P3).

Not limited to a few fixed resolutions: sweeps from min width upward,
plus breakpoint ±1 boundaries and ultrawide samples.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright

OUT = Path(__file__).resolve().parent / "reports" / "p3-shell-responsive-sweep"
BASE = "http://127.0.0.1:5174"
SESSION = {
    "accessToken": "dev-bypass",
    "organizationId": "00000000-0000-4000-8000-000000000010",
    "email": "dev@bypass.local",
}

MIN_WIDTH = 320
MAX_CONTINUOUS = 1600
STEP = 40
BREAKPOINTS = (390, 768, 1024, 1440)
ULTRAWIDE = (1920, 2560, 3440, 3840)
HEIGHT = 900

PAGES = [
    ("customers", "/customers"),
    ("fairs", "/fairs"),
    ("todos", "/todos"),
    ("activities", "/activities"),
    ("admin-backups", "/admin/system/backups"),
    ("di-imports", "/data-integration/imports"),
    ("login", "/login"),
]


def widths_to_test() -> list[int]:
    widths: list[int] = []
    w = MIN_WIDTH
    while w <= MAX_CONTINUOUS:
        widths.append(w)
        w += STEP
    for bp in BREAKPOINTS:
        for delta in (-1, 0, 1):
            widths.append(max(MIN_WIDTH, bp + delta))
    widths.extend(ULTRAWIDE)
    # unique preserve order
    seen: set[int] = set()
    out: list[int] = []
    for value in widths:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


async def measure(page: Page) -> dict:
    return await page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          const overflowX = Math.max(doc.scrollWidth, body.scrollWidth) - doc.clientWidth;
          const shell = document.querySelector('.app-shell');
          const sidebar = document.querySelector('.sidebar, .di-subnav, .admin-subnav');
          const topbar = document.querySelector('.app-topbar');
          const pageShell = document.querySelector('.page-shell, .login-page');
          const modal = document.querySelector('.modal');
          const toolbar = document.querySelector('.filters, .page-header-actions, .adapter-toolbar');

          function rectIssues(el) {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return {
              width: Math.round(r.width),
              left: Math.round(r.left),
              right: Math.round(r.right),
              overflowX: el.scrollWidth - el.clientWidth,
              clipped: style.overflow === 'hidden' && el.scrollWidth > el.clientWidth + 1,
            };
          }

          // crude overlap: topbar vs content
          let overlap = false;
          if (topbar && pageShell) {
            const a = topbar.getBoundingClientRect();
            const b = pageShell.getBoundingClientRect();
            overlap = a.bottom > b.top + 2 && a.top < b.bottom;
          }

          return {
            viewportWidth: window.innerWidth,
            overflowX: overflowX,
            shell: rectIssues(shell),
            sidebar: rectIssues(sidebar),
            topbar: rectIssues(topbar),
            pageShell: rectIssues(pageShell),
            modal: rectIssues(modal),
            toolbar: rectIssues(toolbar),
            pageShellMaxWidth: pageShell ? getComputedStyle(pageShell).maxWidth : null,
            topbarContentOverlap: overlap,
          };
        }"""
    )


def is_fail(m: dict) -> list[str]:
    fails: list[str] = []
    if m.get("overflowX", 0) > 1:
        fails.append(f"horizontal_overflow={m['overflowX']}")
    ps = m.get("pageShell") or {}
    if ps.get("overflowX", 0) > 2:
        fails.append(f"page_shell_overflow={ps['overflowX']}")
    tb = m.get("toolbar") or {}
    if tb.get("overflowX", 0) > 8:
        fails.append(f"toolbar_overflow={tb['overflowX']}")
    # ultrawide: page-shell should clamp (not login)
    if m["viewportWidth"] >= 1920 and m.get("pageShellMaxWidth") not in (None, "none", "100%"):
        # ok if clamped
        pass
    return fails


async def run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    widths = widths_to_test()
    results: list[dict] = []
    failures: list[dict] = []

    session_literal = json.dumps(json.dumps(SESSION))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        await context.add_init_script(
            f"localStorage.setItem('fair-crm.auth.session', {session_literal});"
        )

        for name, path in PAGES:
            page = await context.new_page()
            url = f"{BASE}{path}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(400)
            except Exception as exc:  # noqa: BLE001
                item = {
                    "page": name,
                    "path": path,
                    "viewportWidth": None,
                    "fails": [f"goto_exception:{exc}"],
                }
                failures.append(item)
                results.append(item)
                print(f"ERR  {name} goto: {exc}")
                await page.close()
                continue

            for width in widths:
                try:
                    await page.set_viewport_size({"width": width, "height": HEIGHT})
                    await page.wait_for_timeout(180)
                    m = await measure(page)
                    m["page"] = name
                    m["path"] = path
                    fails = is_fail(m)
                    m["fails"] = fails
                    results.append(m)
                    if fails:
                        failures.append(m)
                        print(f"FAIL {name}@{width}: {', '.join(fails)}")
                    else:
                        print(f"ok   {name}@{width}")
                except Exception as exc:  # noqa: BLE001
                    item = {
                        "page": name,
                        "path": path,
                        "viewportWidth": width,
                        "fails": [f"exception:{exc}"],
                    }
                    failures.append(item)
                    results.append(item)
                    print(f"ERR  {name}@{width}: {exc}")
            await page.close()

        await browser.close()

    report = {
        "min_width": MIN_WIDTH,
        "continuous_to": MAX_CONTINUOUS,
        "step": STEP,
        "breakpoints": list(BREAKPOINTS),
        "ultrawide": list(ULTRAWIDE),
        "pages": [p[0] for p in PAGES],
        "total_checks": len(results),
        "failure_count": len(failures),
        "pass": len(failures) == 0,
        "failures": failures[:80],
        "sample_ultrawide": [r for r in results if r.get("viewportWidth") in ULTRAWIDE][:20],
    }
    (OUT / "sweep.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# P3 Shell Responsive Sweep",
        "",
        f"- Minimum viewport: **{MIN_WIDTH}px**",
        f"- Continuous sweep: **{MIN_WIDTH}→{MAX_CONTINUOUS}** step {STEP}",
        f"- Breakpoint boundaries: {', '.join(str(b) for b in BREAKPOINTS)} (±1)",
        f"- Ultrawide: {', '.join(str(u) for u in ULTRAWIDE)}",
        f"- Checks: **{len(results)}**",
        f"- Failures: **{len(failures)}**",
        f"- Result: **{'PASS' if report['pass'] else 'FAIL'}**",
        "",
    ]
    if failures:
        lines.append("## Failures (sample)")
        lines.append("")
        for f in failures[:40]:
            lines.append(
                f"- `{f.get('page')}@{f.get('viewportWidth')}` — {', '.join(f.get('fails') or [])}"
            )
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUT / 'REPORT.md'} pass={report['pass']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
