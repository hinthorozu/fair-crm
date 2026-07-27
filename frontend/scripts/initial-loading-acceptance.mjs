/**
 * Initial loading UI — representative routes (dev bypass).
 *
 *   FAIR_CRM_API_BASE + FAIR_CRM_BASE_URL
 *   node scripts/initial-loading-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:8001";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";
const DEFAULT_DELAY_MS = Number(process.env.INITIAL_LOAD_API_DELAY_MS || 900);

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(method, path) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "X-Organization-Id": ORG_ID,
    },
  });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  return { status: res.status, json, text };
}

async function seedSession(page) {
  await page.goto(`${BASE}/index.html`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(
    ({ token, orgId }) => {
      localStorage.setItem(
        "fair-crm.auth.session",
        JSON.stringify({
          accessToken: token,
          refreshToken: token,
          organizationId: orgId,
        }),
      );
    },
    { token: TOKEN, orgId: ORG_ID },
  );
}

function shouldDelayGet(url) {
  try {
    const u = new URL(url);
    if (!u.pathname.includes("/api/")) return false;
    return (
      /\/api\/v1\/(customers|fairs|operations|activities|todos|imports)/.test(u.pathname) ||
      /\/api\/v1\/admin\//.test(u.pathname) ||
      /\/api\/v1\/system\//.test(u.pathname) ||
      /data-operations/.test(u.pathname) ||
      /import/.test(u.pathname)
    );
  } catch {
    return false;
  }
}

/** Single route handler; mutate delayMsRef.current to enable/disable delay. */
async function installApiDelayControl(page, delayMsRef) {
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const delay = delayMsRef.current;
    if (delay > 0 && req.method() === "GET" && shouldDelayGet(req.url())) {
      await new Promise((r) => setTimeout(r, delay));
    }
    await route.continue();
  });
}

async function assertInitialLoadingVisible(page, label) {
  const loading = page.locator(".loading-state, .table-skeleton");
  await loading.first().waitFor({ state: "visible", timeout: 15000 });
  const emptyWhileLoading = await page.locator(".empty-state").count();
  assert(emptyWhileLoading === 0, `${label}: empty-state shown during initial load`);
  console.log(`${label}: initial_loading_ok`);
}

async function assertSettledNotBlank(page, label) {
  await page.waitForFunction(
    () => {
      const loading = document.querySelectorAll(".loading-state, .table-skeleton").length;
      const shell = document.querySelector(".page-shell, .app-main, main");
      const rowsOrEmpty =
        document.querySelectorAll(
          ".data-table tbody tr, .empty-state, .duplicate-group-detail, .backup-database-cell",
        ).length > 0 ||
        Boolean(document.querySelector(".server-data-table-frame, .page-shell"));
      return loading === 0 && Boolean(shell) && rowsOrEmpty;
    },
    { timeout: 60000 },
  );
  const loadingLeft = await page.locator(".loading-state, .table-skeleton").count();
  assert(loadingLeft === 0, `${label}: loading still visible after settle`);
  console.log(`${label}: settled_ok`);
}

async function assertSilentRefreshKeepsRows(page, label, delayMsRef) {
  const rows = page.locator(".data-table tbody tr");
  const before = await rows.count();
  if (before === 0) {
    console.log(`${label}: silent_refresh_skip (no rows)`);
    return;
  }

  const refreshBtn = page.getByRole("button", { name: /Yenile|Refresh/i }).first();
  if ((await refreshBtn.count()) === 0) {
    console.log(`${label}: silent_refresh_skip (no refresh button)`);
    return;
  }

  delayMsRef.current = 1200;
  const clickPromise = refreshBtn.click();
  await page.waitForTimeout(250);
  const skeletonDuring = await page.locator(".table-skeleton").count();
  const rowsDuring = await rows.count();
  assert(rowsDuring > 0, `${label}: rows disappeared during refresh`);
  assert(skeletonDuring === 0, `${label}: full table skeleton during refresh`);
  await clickPromise.catch(() => undefined);
  await page.waitForTimeout(1600);
  delayMsRef.current = 0;
  const rowsAfter = await rows.count();
  assert(rowsAfter > 0, `${label}: rows gone after refresh`);
  console.log(`${label}: silent_refresh_ok`);
}

async function visitWithInitialLoadChecks(page, path, label, delayMsRef) {
  delayMsRef.current = DEFAULT_DELAY_MS;
  await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await assertInitialLoadingVisible(page, label);
  await assertSettledNotBlank(page, label);
  delayMsRef.current = 0;
  await assertSilentRefreshKeepsRows(page, label, delayMsRef);
}

async function resolveDuplicateRunId() {
  const known = [
    "30746872-a92d-4731-bc9a-71b8ceccefcf",
    "0e53a8e1-b53e-46b0-8f28-9843efd853f3",
    "dfff1a9e-32d9-4525-903d-423f0d5c6a41",
  ];
  for (const id of known) {
    const res = await api("GET", `/api/v1/admin/data-operations/runs/${id}`);
    if (res.status === 200 && (res.json?.result === "success" || res.json?.status === "completed")) {
      return id;
    }
  }
  // Create a fresh run if none known
  const created = await fetch(`${API}/api/v1/admin/data-operations/duplicate_customer_analysis/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "X-Organization-Id": ORG_ID,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ params: { group_by: "company_name" } }),
  });
  const body = await created.json().catch(() => null);
  const runId = body?.run_id || body?.id || body?.run?.id;
  if (!runId) return null;
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const poll = await api("GET", `/api/v1/admin/data-operations/runs/${runId}`);
    if (poll.json?.result === "success" || poll.json?.status === "completed") return runId;
    if (poll.json?.result === "failed" || poll.json?.status === "failed") break;
  }
  return null;
}

const ROUTES = [
  { path: "/customers", label: "Customers" },
  { path: "/fairs", label: "Fairs" },
  { path: "/operations", label: "Operations" },
  { path: "/admin/system/backups", label: "Backup/Restore" },
  { path: "/data-integration/imports", label: "Import jobs" },
];

async function main() {
  const health = await fetch(`${API}/health`).catch(() => null);
  if (!health?.ok) {
    console.error("API unreachable — set FAIR_CRM_API_BASE and start backend");
    process.exit(2);
  }

  const duplicateRunId = await resolveDuplicateRunId();
  const duplicateRunPath = duplicateRunId
    ? `/operations/duplicate-check/runs/${duplicateRunId}`
    : null;
  console.log("duplicate_run", duplicateRunId);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const delayMsRef = { current: 0 };
  await installApiDelayControl(page, delayMsRef);
  await seedSession(page);

  const results = [];

  for (const route of ROUTES) {
    try {
      await visitWithInitialLoadChecks(page, route.path, route.label, delayMsRef);
      results.push({ route: route.label, status: "PASS" });
    } catch (err) {
      results.push({ route: route.label, status: "FAIL", error: String(err.message || err) });
    }
  }

  if (duplicateRunPath) {
    try {
      delayMsRef.current = DEFAULT_DELAY_MS;
      await page.goto(`${BASE}${duplicateRunPath}`, {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      });
      await assertInitialLoadingVisible(page, "Duplicate Groups");
      await assertSettledNotBlank(page, "Duplicate Groups");
      delayMsRef.current = 0;
      await assertSilentRefreshKeepsRows(page, "Duplicate Groups", delayMsRef);
      results.push({ route: "Duplicate Groups", status: "PASS" });

      const groupsApi = await api(
        "GET",
        `/api/v1/admin/data-operations/runs/${duplicateRunId}/dataset/duplicate-groups?page=1&page_size=5`,
      );
      const firstGroupKey = groupsApi.json?.items?.[0]?.group_key;
      if (firstGroupKey) {
        delayMsRef.current = DEFAULT_DELAY_MS;
        const detailPath = `${duplicateRunPath}?group=${encodeURIComponent(firstGroupKey)}`;
        await page.goto(`${BASE}${detailPath}`, {
          waitUntil: "domcontentloaded",
          timeout: 60000,
        });
        await assertInitialLoadingVisible(page, "Duplicate Group Detail");
        await assertSettledNotBlank(page, "Duplicate Group Detail");
        delayMsRef.current = 0;
        // Detail should show LoadingState then merge UI / error — not empty blank
        const detailOk = await page.locator(".duplicate-group-detail, .loading-state, .banner").count();
        assert(detailOk > 0 || (await page.locator(".page-shell").count()) > 0, "detail shell missing");
        results.push({ route: "Duplicate Group Detail", status: "PASS", groupKey: firstGroupKey });
      } else {
        console.log("Duplicate Group Detail: SKIP (no groups on run)");
        results.push({
          route: "Duplicate Group Detail",
          status: "SKIP",
          error: "no groups on successful run",
        });
      }
    } catch (err) {
      results.push({
        route: "Duplicate Groups / Detail",
        status: "FAIL",
        error: String(err.message || err),
      });
    }
  } else {
    results.push({
      route: "Duplicate Groups",
      status: "SKIP",
      error: "no successful duplicate run in API",
    });
    results.push({
      route: "Duplicate Group Detail",
      status: "SKIP",
      error: "no successful duplicate run in API",
    });
  }

  try {
    const ops = await api("GET", "/api/v1/operations?page=1&page_size=100");
    const bulk = (ops.json?.items || []).find(
      (o) =>
        o.operation_type === "bulk_email" ||
        o.operation_type === "fair_bulk_email" ||
        String(o.operation_key || "").includes("bulk_email"),
    );
    if (bulk?.id) {
      delayMsRef.current = DEFAULT_DELAY_MS;
      await page.goto(`${BASE}/operations/${bulk.id}`, {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      });
      await assertInitialLoadingVisible(page, "Bulk Email recipients");
      await assertSettledNotBlank(page, "Bulk Email recipients");
      delayMsRef.current = 0;
      results.push({ route: "Bulk Email recipients", status: "PASS", operationId: bulk.id });
    } else {
      results.push({
        route: "Bulk Email recipients",
        status: "SKIP",
        error: "no bulk_email operation",
      });
    }
  } catch (err) {
    results.push({
      route: "Bulk Email recipients",
      status: "FAIL",
      error: String(err.message || err),
    });
  }

  await browser.close();

  console.log(JSON.stringify({ results, api: API, base: BASE }, null, 2));
  const failed = results.filter((r) => r.status === "FAIL");
  if (failed.length) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
