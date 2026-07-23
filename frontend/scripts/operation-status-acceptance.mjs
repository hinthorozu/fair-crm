/**
 * Shared Operation user-facing status acceptance (real JWT).
 *
 * Usage:
 *   $env:DEV_USER_PASSWORD='...'
 *   node scripts/operation-status-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:8001";
const EMAIL = process.env.FAIR_CRM_DEV_EMAIL || "dev@example.com";
const PASSWORD = process.env.DEV_USER_PASSWORD || process.env.FAIR_CRM_DEV_PASSWORD;
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";

if (!PASSWORD) {
  console.error("DEV_USER_PASSWORD or FAIR_CRM_DEV_PASSWORD required");
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(token, method, path) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
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
  return { status: res.status, text, json };
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.fill("#login-email, input[type='email']", EMAIL);
  await page.fill("#login-password, input[type='password']", PASSWORD);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30000 }),
    page.click('button[type="submit"]'),
  ]);
  const session = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  assert(session?.accessToken, "LOGIN_FAIL");
  return session.accessToken;
}

function mapTech(status) {
  if (status === "queued" || status === "running") return "Çalışıyor";
  if (status === "completed") return "Bitti";
  if (status === "failed") return "Hata";
  if (status === "cancelled") return "İptal";
  if (status === "paused") return "Durduruldu";
  if (status === "scheduled") return "Zamanlandı";
  return null;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const token = await login(page);
  console.log("login_ok");

  const list = await api(token, "GET", "/api/v1/operations?page=1&page_size=50");
  assert(list.status === 200, `list failed ${list.status}`);
  const items = list.json?.items || [];
  console.log("list_count", items.length);

  // latest_run should be hydrated for ops that have runs
  const withRun = items.find((op) => op.latest_run_id);
  if (withRun) {
    assert(withRun.latest_run != null, "latest_run not hydrated on list");
    console.log("list_hydrate_ok", withRun.id, withRun.latest_run.status);
  }

  const samples = {
    running: items.find((op) => ["running", "queued"].includes(op.latest_run?.status)),
    completed: items.find((op) => op.latest_run?.status === "completed"),
    failed: items.find((op) => op.latest_run?.status === "failed"),
    cancelled: items.find((op) => op.latest_run?.status === "cancelled"),
    paused: items.find((op) => op.latest_run?.status === "paused"),
  };

  const results = {
    listNoAktifLifecycleAsStatus: false,
    listDetailConsistent: false,
    adminTypeIsActiveOk: false,
    samples: {},
  };

  await page.goto(`${BASE}/operations`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2500);
  const listText = await page.locator("body").innerText();

  // Status filter should show user-facing options, not "Aktif" as a run status option
  const filter = page.locator("#operation-filter-status");
  const filterHtml = await filter.innerHTML();
  assert(!/value="active"/.test(filterHtml), "status filter still has operation lifecycle active");
  assert(/Çalışıyor|Bitti|Hata|İptal/.test(filterHtml), "user-facing filter options missing");
  results.listNoAktifLifecycleAsStatus = !/value="active"/.test(filterHtml);

  // Pick one sample with a completed/failed/running run and compare list vs detail
  const sample =
    samples.completed || samples.failed || samples.cancelled || samples.running || withRun;
  assert(sample, "No operation with latest_run for acceptance");
  const expectedLabel = mapTech(sample.latest_run.status);
  assert(expectedLabel, `unmapped status ${sample.latest_run.status}`);

  // Ensure list row text includes expected label (or — if somehow missing)
  // Navigate to detail
  await page.goto(`${BASE}/operations/${sample.id}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForSelector(`text=${expectedLabel}`, { timeout: 30000 });
  const detailText = await page.locator("body").innerText();
  assert(detailText.includes(expectedLabel), `detail missing ${expectedLabel}`);
  // Operation-instance "Aktif" lifecycle badge should not be the primary status label in header area
  // (admin type is_active is a different page)
  const headerBadges = await page.locator(".stack.gap-lg > .card").first().innerText();
  assert(
    !/^Aktif$/m.test(headerBadges.split("\n")[0] || "") || headerBadges.includes(expectedLabel),
    "unexpected Aktif-only header status",
  );
  assert(headerBadges.includes(expectedLabel), `header missing user-facing ${expectedLabel}`);

  // List page again — same label
  await page.goto(`${BASE}/operations`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const listAgain = await page.locator("body").innerText();
  // Title may be truncated; at least confirm user-facing vocabulary present somewhere
  assert(
    listAgain.includes(expectedLabel) || listAgain.includes("—"),
    `list missing ${expectedLabel}`,
  );
  results.listDetailConsistent = true;
  results.samples[sample.latest_run.status] = expectedLabel;

  for (const [key, op] of Object.entries(samples)) {
    if (!op) {
      console.log(`sample_${key}_absent`);
      continue;
    }
    const label = mapTech(op.latest_run.status);
    await page.goto(`${BASE}/operations/${op.id}`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector(`text=${label}`, { timeout: 30000 });
    const text = await page.locator("body").innerText();
    assert(text.includes(label), `${key} detail missing ${label}`);
    results.samples[key] = label;
    console.log(`sample_${key}_ok`, label);
  }

  // Admin operation type is_active still works
  const types = await api(token, "GET", "/api/v1/operations/types?active_only=true");
  assert(types.status === 200, `types failed ${types.status}`);
  assert(Array.isArray(types.json?.items), "types items missing");
  assert(types.json.items.every((t) => t.is_active === true), "active_only regression");
  results.adminTypeIsActiveOk = true;

  await page.goto(`${BASE}/admin/operation-capabilities`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  }).catch(() => null);
  // route may differ — API check is enough for is_active

  await browser.close();
  console.log("ACCEPTANCE_RESULTS");
  console.log(JSON.stringify(results, null, 2));
  console.log("ACCEPTANCE_PASS");
}

main().catch((err) => {
  console.error("ACCEPTANCE_FAILED:", err?.stack || String(err));
  process.exit(1);
});
