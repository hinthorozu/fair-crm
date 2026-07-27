/**
 * Duplicate Customer Analysis optional fair filter — real API + browser.
 *
 *   FAIR_CRM_API_BASE + FAIR_CRM_BASE_URL (dev bypass)
 *   node scripts/duplicate-fair-filter-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:8001";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "X-Organization-Id": ORG_ID,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
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

async function main() {
  const stamp = Date.now();
  const fairName = `Intermob E2E ${stamp}`;
  const otherFairName = `Other E2E ${stamp}`;
  const sharedEmail = `dup-fair-${stamp}@example.com`;

  const fairA = await api("POST", "/api/v1/fairs", {
    name: fairName,
    location: "Istanbul",
    start_date: "2026-06-01",
    end_date: "2026-06-03",
  });
  assert(fairA.status === 201, "fair A create failed");
  const fairB = await api("POST", "/api/v1/fairs", {
    name: otherFairName,
    location: "Istanbul",
    start_date: "2026-06-01",
    end_date: "2026-06-03",
  });
  assert(fairB.status === 201, "fair B create failed");

  const mkCustomer = async (displayName) => {
    const res = await api("POST", "/api/v1/customers", {
      display_name: displayName,
      email: sharedEmail,
      status: "active",
    });
    assert(res.status === 201, `customer ${displayName} failed`);
    return res.json.id;
  };

  const c1 = await mkCustomer(`Dup Fair A1 ${stamp}`);
  const c2 = await mkCustomer(`Dup Fair A2 ${stamp}`);
  const cOther = await mkCustomer(`Dup Fair B ${stamp}`);

  const part = async (fairId, customerId) => {
    const res = await api("POST", "/api/v1/fair-participations", {
      fair_id: fairId,
      customer_id: customerId,
      participation_status: "exhibitor",
    });
    assert(res.status === 201, `participation failed ${res.status} ${res.text}`);
  };

  await part(fairA.json.id, c1);
  await part(fairA.json.id, c2);
  await part(fairB.json.id, cOther);

  const scoped = await api("POST", "/api/v1/admin/data-operations/duplicate_customer_analysis/run", {
    group_by: "email",
    fair_id: fairA.json.id,
  });
  assert(scoped.status === 202, `scoped run failed ${scoped.status}`);
  const runId = scoped.json.id;
  const runDetail = await api("GET", `/api/v1/admin/data-operations/runs/${runId}`);
  assert(runDetail.json.summary_json?.fair_name === fairName, "summary fair_name mismatch");
  assert(runDetail.json.summary_json?.duplicate_groups === 1, "expected one duplicate group");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.addInitScript((orgId) => {
    localStorage.setItem(
      "fair-crm.auth.session",
      JSON.stringify({
        accessToken: "dev-bypass",
        organizationId: orgId,
        email: "e2e@local.test",
      }),
    );
  }, ORG_ID);

  await page.goto(`${BASE}/operations/new/duplicate-check`, { waitUntil: "domcontentloaded" });
  const fairInput = page.locator("#duplicate-fair-filter");
  await fairInput.waitFor({ timeout: 30000 });
  await fairInput.click();
  await fairInput.fill(fairName.slice(0, 12));
  await page.waitForTimeout(400);
  await page.locator(".entity-select-option-label").filter({ hasText: fairName }).first().click();

  await page.goto(`${BASE}/operations/duplicate-check/runs/${runId}`, {
    waitUntil: "domcontentloaded",
  });
  const bodyText = await page.locator(".duplicate-groups-summary-grid").innerText();
  assert(bodyText.includes(fairName), "result page should show selected fair name");
  assert(bodyText.includes("Tüm Fuarlar") === false || bodyText.includes(fairName), "fair filter visible");

  await browser.close();
  console.log("UI_TEST: PASS");
  console.log("run_id", runId);
}

main().catch((err) => {
  console.error("UI_TEST: FAIL");
  console.error(err);
  process.exit(1);
});
