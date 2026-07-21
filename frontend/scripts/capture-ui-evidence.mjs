/**
 * FAIR CRM — Full UI evidence capture
 * Captures route × viewport screenshots + layout metrics.
 *
 * AUTO_FROM_APPROUTE — production routes are merged from `src/App.tsx`
 * `AppRoute` union so new routes cannot stay outside responsive smoke coverage.
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(__dirname, "..");
const APP_TSX = path.join(FRONTEND_ROOT, "src", "App.tsx");

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5175";
/** Login captured without auth bypass (otherwise redirects to dashboard). */
const LOGIN_BASE = process.env.FAIR_LOGIN_BASE_URL || "http://127.0.0.1:5176";
const OUT = path.resolve("reports/full-ui-evidence");
const SHOTS = path.join(OUT, "screenshots");

/** Marker consumed by inventory FINAL/route gate. */
const AUTO_FROM_APPROUTE = true;

function extractAppRoutes() {
  const text = fs.readFileSync(APP_TSX, "utf8");
  const m = text.match(/type\s+AppRoute\s*=([\s\S]*?);/);
  if (!m) return [];
  return [...new Set([...m[1].matchAll(/["'](\/[^"']+)["']/g)].map((x) => x[1]))].sort();
}

const CUSTOMER = process.env.FAIR_CUSTOMER_ID || "96715255-5b1b-5a4e-a8d6-1efa8e010da5";
const FAIR = process.env.FAIR_FAIR_ID || "185f1197-beb6-4d98-a53f-1ed7e503ae14";
const TODO = process.env.FAIR_TODO_ID || "14dbd7db-9a64-4608-81f5-a13bbae64945";
const ADAPTER = process.env.FAIR_ADAPTER_KEY || "customer_contact_enrichment";
const RUN_ID = process.env.FAIR_RUN_ID || "";
const BATCH_ID = process.env.FAIR_BATCH_ID || "";
const DATAOP_RUN_ID = process.env.FAIR_DATAOP_RUN_ID || "";
const DATAOP_KEY = process.env.FAIR_DATAOP_KEY || "";

const WIDTHS = [320, 390, 767, 768, 769, 1023, 1024, 1025, 1439, 1440, 1441, 1920, 2560, 3440, 3840];
const MATRIX_WIDTHS = [320, 390, 768, 1024, 1440, 1920, 2560, 3440, 3840];

function slug(route) {
  return route
    .replace(/^\//, "")
    .replace(/[/?&=:]/g, "_")
    .replace(/_+/g, "_")
    .replace(/_$/g, "") || "root";
}

async function discoverIds(page) {
  const ids = {
    customer: CUSTOMER,
    fair: FAIR,
    todo: TODO,
    adapter: ADAPTER,
    runId: RUN_ID || null,
    batchId: BATCH_ID || null,
    dataOpRunId: DATAOP_RUN_ID || null,
    dataOpKey: DATAOP_KEY || null,
  };

  await page.goto(`${BASE}/data-integration/run-history`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(800);
  const runHref = await page.evaluate(() => {
    const a = Array.from(document.querySelectorAll("a,button")).find((el) => {
      const href = el.getAttribute("href") || "";
      return href.includes("/data-integration/runs/") || (el.textContent || "").match(/run/i);
    });
    // Prefer table entity links / buttons that navigate
    const links = Array.from(document.querySelectorAll("a[href*='/data-integration/runs/']"));
    if (links[0]) return links[0].getAttribute("href");
    const btn = Array.from(document.querySelectorAll("button")).find((b) => /run|detay/i.test(b.textContent || ""));
    return null;
  });
  // Click first expandable or entity link if present
  const runFromDom = await page.evaluate(() => {
    const text = document.body.innerText || "";
    const m = text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
    return m ? m[0] : null;
  });
  if (!ids.runId && runFromDom) ids.runId = runFromDom;

  await page.goto(`${BASE}/data-integration/imports`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(800);
  const batchFromDom = await page.evaluate(() => {
    const href = Array.from(document.querySelectorAll("a[href*='/imports/continue/'], button"))
      .map((el) => el.getAttribute("href") || el.getAttribute("data-batch-id") || "")
      .find((h) => h.includes("/continue/"));
    if (href) {
      const m = href.match(/continue\/([^/?#]+)/);
      if (m) return m[1];
    }
    const text = document.body.innerText || "";
    const m = text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
    return m ? m[0] : null;
  });
  if (!ids.batchId && batchFromDom) ids.batchId = batchFromDom;

  await page.goto(`${BASE}/admin/data-operations`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1000);
  const dataOp = await page.evaluate(() => {
    const href = Array.from(document.querySelectorAll("a[href*='/admin/data-operations/runs/']"))
      .map((a) => a.getAttribute("href"))
      .find(Boolean);
    if (href) {
      const m = href.match(/runs\/([^/?#]+)/);
      const op = new URL(href, location.origin).searchParams.get("operation");
      return { runId: m?.[1] || null, key: op };
    }
    // Try buttons that open results
    const btns = Array.from(document.querySelectorAll("button,a"));
    for (const b of btns) {
      const t = (b.textContent || "").toLowerCase();
      if (t.includes("sonuç") || t.includes("result") || t.includes("detay")) {
        return { hint: t.slice(0, 40) };
      }
    }
    return null;
  });
  if (!ids.dataOpRunId && dataOp?.runId) {
    ids.dataOpRunId = dataOp.runId;
    ids.dataOpKey = dataOp.key;
  }

  // Click result link if available
  if (!ids.dataOpRunId) {
    const clicked = await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll("button,a")).find((b) =>
        /sonuç|result|görüntüle|detay/i.test(b.textContent || ""),
      );
      if (el) {
        el.click();
        return true;
      }
      return false;
    });
    if (clicked) {
      await page.waitForTimeout(1200);
      const url = page.url();
      const m = url.match(/\/admin\/data-operations\/runs\/([^/?#]+)/);
      if (m) {
        ids.dataOpRunId = decodeURIComponent(m[1]);
        ids.dataOpKey = new URL(url).searchParams.get("operation");
      }
    }
  }

  // Adapter list alternate keys
  await page.goto(`${BASE}/data-integration/adapters`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(800);
  const adapters = await page.evaluate(() =>
    Array.from(document.querySelectorAll("a[href*='/data-integration/adapters/']"))
      .map((a) => decodeURIComponent((a.getAttribute("href") || "").split("/").pop() || ""))
      .filter(Boolean),
  );
  if (adapters.length) ids.adapter = adapters[0];
  ids.adapters = adapters;

  return ids;
}

function buildRoutes(ids) {
  const routes = [
    { route: "/login", url: "/login", kind: "static", production: true },
    { route: "/dashboard", url: "/dashboard", kind: "static", production: true },
    { route: "/customers", url: "/customers", kind: "static", production: true },
    { route: "/customers/:id", url: `/customers/${ids.customer}`, kind: "detail", production: true },
    { route: "/fairs", url: "/fairs", kind: "static", production: true },
    { route: "/fairs/:id", url: `/fairs/${ids.fair}`, kind: "detail", production: true },
    { route: "/fairs/:id/enrichment", url: `/fairs/${ids.fair}/enrichment`, kind: "detail", production: true },
    { route: "/todos", url: "/todos", kind: "static", production: true },
    { route: "/todos/:id", url: `/todos/${ids.todo}`, kind: "detail", production: true },
    { route: "/follow-ups", url: "/follow-ups", kind: "static", production: true },
    { route: "/activities", url: "/activities", kind: "static", production: true },
    { route: "/data-integration/imports", url: "/data-integration/imports", kind: "di", production: true },
    { route: "/data-integration/imports/new", url: "/data-integration/imports/new", kind: "di", production: true },
    { route: "/data-integration/imports/fair/:fairId", url: `/data-integration/imports/fair/${ids.fair}`, kind: "di-param", production: true },
    {
      route: "/data-integration/imports/continue/:batchId",
      url: ids.batchId ? `/data-integration/imports/continue/${ids.batchId}` : null,
      kind: "di-param",
      production: true,
    },
    { route: "/data-integration/jobs", url: "/data-integration/jobs", kind: "di", production: true },
    { route: "/data-integration/reports", url: "/data-integration/reports", kind: "di", production: true },
    { route: "/data-integration/adapters", url: "/data-integration/adapters", kind: "di", production: true },
    {
      route: "/data-integration/adapters/:adapterKey",
      url: `/data-integration/adapters/${encodeURIComponent(ids.adapter)}`,
      kind: "di-param",
      production: true,
    },
    { route: "/data-integration/run-history", url: "/data-integration/run-history", kind: "di", production: true },
    {
      route: "/data-integration/runs/:runId",
      url: ids.runId
        ? `/data-integration/runs/${encodeURIComponent(ids.runId)}?adapter_key=${encodeURIComponent(ids.adapter)}`
        : null,
      kind: "di-param",
      production: true,
    },
    { route: "/data-integration/scraper-test", url: "/data-integration/scraper-test", kind: "di", production: true },
    { route: "/data-integration/enrichment", url: "/data-integration/enrichment", kind: "di", production: true },
    { route: "/admin/system/backups", url: "/admin/system/backups", kind: "admin", production: true },
    { route: "/admin/smtp-operations/accounts", url: "/admin/smtp-operations/accounts", kind: "admin", production: true },
    { route: "/admin/smtp-operations/templates", url: "/admin/smtp-operations/templates", kind: "admin", production: true },
    { route: "/admin/smtp-operations/mail-operations", url: "/admin/smtp-operations/mail-operations", kind: "admin", production: true },
    { route: "/admin/data-operations", url: "/admin/data-operations", kind: "admin", production: true },
    {
      route: "/admin/data-operations/runs/:runId",
      url: ids.dataOpRunId
        ? `/admin/data-operations/runs/${encodeURIComponent(ids.dataOpRunId)}${
            ids.dataOpKey ? `?operation=${encodeURIComponent(ids.dataOpKey)}` : ""
          }`
        : null,
      kind: "admin-param",
      production: true,
    },
    { route: "/imports", url: "/imports", kind: "legacy-redirect", production: true },
    { route: "/imports/fair/:fairId", url: `/imports/fair/${ids.fair}`, kind: "legacy-redirect", production: true },
    { route: "/dev/customers-responsive-pilot", url: "/dev/customers-responsive-pilot", kind: "dev", production: false },
    { route: "/dev/table-standard-smoke", url: "/dev/table-standard-smoke", kind: "dev", production: false },
  ];

  // AUTO_FROM_APPROUTE: ensure every AppRoute is in the smoke catalog.
  const known = new Set(routes.map((r) => r.route));
  for (const route of extractAppRoutes()) {
    if (known.has(route)) continue;
    const url = route.includes(":")
      ? null
      : route;
    routes.push({
      route,
      url,
      kind: "auto-from-approute",
      production: true,
    });
    known.add(route);
  }
  if (!AUTO_FROM_APPROUTE) {
    throw new Error("AUTO_FROM_APPROUTE marker must remain true for UI governance");
  }
  return routes;
}

async function measure(page) {
  return page.evaluate(() => {
    const d = document.documentElement;
    const b = document.body;
    const overflowX = Math.max(0, Math.max(d.scrollWidth, b.scrollWidth) - d.clientWidth);
    const overflowY = Math.max(0, Math.max(d.scrollHeight, b.scrollHeight) - d.clientHeight);
    const stretched = Array.from(document.querySelectorAll(".checkbox-field,.radio-field,.output-field-row")).filter(
      (el) => el.getBoundingClientRect().width > 480,
    ).length;
    const nativeChecks = Array.from(document.querySelectorAll('input[type="checkbox"],input[type="radio"]')).filter(
      (el) => {
        const s = getComputedStyle(el);
        return s.appearance !== "none" && s.webkitAppearance !== "none";
      },
    ).length;
    return {
      overflowX,
      overflowY,
      stretched,
      nativeChecks,
      title: document.title,
      h1: document.querySelector("h1")?.textContent?.trim() || null,
    };
  });
}

async function main() {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ bypassCSP: true });
  const page = await context.newPage();

  console.log("Discovering IDs…");
  const ids = await discoverIds(page);
  fs.writeFileSync(path.join(OUT, "discovered-ids.json"), JSON.stringify(ids, null, 2));
  console.log(JSON.stringify(ids, null, 2));

  const routes = buildRoutes(ids);
  const results = [];

  for (const r of routes) {
    if (!r.url) {
      for (const w of WIDTHS) {
        results.push({
          route: r.route,
          url: null,
          width: w,
          status: "NOT_VERIFIED",
          reason: "missing-param-id",
          kind: r.kind,
          production: r.production,
        });
      }
      continue;
    }

    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: width >= 1440 ? 1080 : 900 });
      const origin = r.route === "/login" ? LOGIN_BASE : BASE;
      const fullUrl = `${origin}${r.url}`;
      let status = "PASS";
      let reason = "";
      let metrics = {};
      try {
        await page.goto(fullUrl, { waitUntil: "networkidle", timeout: 45000 });
        await page.waitForTimeout(500);
        metrics = await measure(page);
        if (r.route === "/login" && !String(metrics.title || "").toLowerCase().includes("giriş") && !String(metrics.h1 || "").includes("FAIR CRM")) {
          // Accept login brand h1; reject dashboard redirect
          if (String(metrics.h1 || "") === "Dashboard") {
            status = "FAIL";
            reason = "login-redirected-to-dashboard";
          }
        }
        if (r.route === "/login" && String(metrics.h1 || "") === "Dashboard") {
          status = "FAIL";
          reason = "login-redirected-to-dashboard";
        }
        if (metrics.overflowX > 0) {
          status = "FAIL";
          reason = `overflowX=${metrics.overflowX}`;
        } else if (metrics.stretched > 0) {
          status = "FAIL";
          reason = `stretchedControls=${metrics.stretched}`;
        } else if (metrics.nativeChecks > 0) {
          status = "FAIL";
          reason = `nativeCheckboxRadio=${metrics.nativeChecks}`;
        }
      } catch (err) {
        status = "FAIL";
        reason = String(err.message || err).slice(0, 160);
      }

      const file = `${slug(r.route)}__w${width}.png`;
      const shotPath = path.join(SHOTS, file);
      try {
        await page.screenshot({ path: shotPath, fullPage: false });
      } catch (err) {
        status = "FAIL";
        reason = (reason ? reason + "; " : "") + "screenshot-failed";
      }

      results.push({
        route: r.route,
        url: r.url,
        width,
        status,
        reason,
        kind: r.kind,
        production: r.production,
        screenshot: `screenshots/${file}`,
        metrics,
      });
      console.log(`${status} ${r.route} @${width} ${reason}`);
    }
  }

  fs.writeFileSync(path.join(OUT, "capture-results.json"), JSON.stringify({ ids, results }, null, 2));

  // Matrix markdown for MATRIX_WIDTHS only (plus note BP extras in BREAKPOINT_QA)
  const routeList = [...new Map(routes.map((r) => [r.route, r])).values()];
  const lines = [
    "# ROUTE_MATRIX",
    "",
    `Base URL: \`${BASE}\``,
    "",
    `Discovered IDs: \`${JSON.stringify(ids)}\``,
    "",
    "| Route | Test URL | 320 | 390 | 768 | 1024 | 1440 | 1920 | 2560 | 3440 | 3840 | Sonuç |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
  ];
  for (const r of routeList) {
    const cells = MATRIX_WIDTHS.map((w) => {
      const hit = results.find((x) => x.route === r.route && x.width === w);
      if (!hit) return "NOT VERIFIED";
      if (hit.status === "PASS") return "PASS";
      if (hit.status === "NOT_VERIFIED") return "NOT VERIFIED";
      return "FAIL";
    });
    const overall = cells.every((c) => c === "PASS")
      ? "PASS"
      : cells.some((c) => c === "NOT VERIFIED")
        ? "NOT VERIFIED"
        : "FAIL";
    lines.push(`| \`${r.route}\` | \`${r.url || "—"}\` | ${cells.join(" | ")} | ${overall} |`);
  }
  fs.writeFileSync(path.join(OUT, "ROUTE_MATRIX.md"), lines.join("\n") + "\n");

  // Breakpoint QA
  const bpWidths = [767, 768, 769, 1023, 1024, 1025, 1439, 1440, 1441];
  const bpLines = [
    "# BREAKPOINT_QA",
    "",
    "CSS breakpoints observed: 767/768, 1023/1024, 1440 (+ legacy 768 max-width variants).",
    "",
    "| Route | 767 | 768 | 769 | 1023 | 1024 | 1025 | 1439 | 1440 | 1441 | Sonuç |",
    "|---|---|---|---|---|---|---|---|---|---|---|",
  ];
  for (const r of routeList.filter((x) => x.production)) {
    const cells = bpWidths.map((w) => {
      const hit = results.find((x) => x.route === r.route && x.width === w);
      if (!hit) return "NOT VERIFIED";
      return hit.status === "PASS" ? "PASS" : hit.status === "NOT_VERIFIED" ? "NOT VERIFIED" : "FAIL";
    });
    const overall = cells.every((c) => c === "PASS")
      ? "PASS"
      : cells.some((c) => c === "NOT VERIFIED")
        ? "NOT VERIFIED"
        : "FAIL";
    bpLines.push(`| \`${r.route}\` | ${cells.join(" | ")} | ${overall} |`);
  }
  fs.writeFileSync(path.join(OUT, "BREAKPOINT_QA.md"), bpLines.join("\n") + "\n");

  const failCount = results.filter((r) => r.status === "FAIL").length;
  const nvCount = results.filter((r) => r.status === "NOT_VERIFIED").length;
  console.log(JSON.stringify({ total: results.length, fails: failCount, notVerified: nvCount }, null, 2));

  await browser.close();
  process.exit(failCount || nvCount ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});
