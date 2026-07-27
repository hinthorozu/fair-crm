/**
 * Agrozan duplicate merge — real UI on reference run (requires live API + Vite bypass).
 *
 *   FAIR_CRM_BASE_URL=http://127.0.0.1:54970
 *   FAIR_CRM_API_BASE=http://127.0.0.1:54960
 *   node scripts/agrozan-merge-ui-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:54970";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:54960";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";
const RUN_ID = process.env.DUP_MERGE_RUN_ID || "30746872-a92d-4731-bc9a-71b8ceccefcf";
const GROUP_SEARCH = process.env.DUP_MERGE_GROUP_SEARCH || "agrozan";

async function apiGet(path) {
  const res = await fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${TOKEN}`, "X-Organization-Id": ORG_ID },
  });
  const text = await res.text();
  return { status: res.status, json: text ? JSON.parse(text) : null, text };
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function main() {
  const health = await apiGet("/api/v1/admin/data-operations");
  assert(health.status === 200, `API unavailable (${API}): ${health.status} ${health.text}`);

  const groups = await apiGet(
    `/api/v1/admin/data-operations/runs/${RUN_ID}/dataset/duplicate-groups?search=${encodeURIComponent(GROUP_SEARCH)}&page=1&page_size=5`,
  );
  assert(groups.json?.items?.length >= 1, "Agrozan group not found on run");
  const groupKey = groups.json.items[0].group_key;

  const mergeExecuteStatuses = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("response", (res) => {
    if (res.url().includes("/merge-execute")) mergeExecuteStatuses.push(res.status());
  });

  const groupParam = encodeURIComponent(groupKey).replace(/%20/g, "+");
  const url = `${BASE}/operations/duplicate-check/runs/${RUN_ID}?operation=duplicate_customer_analysis&group=${groupParam}`;
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForSelector(".duplicate-group-customer-card", { timeout: 45000 });

  await page.waitForFunction(
    () => {
      const btn = document.querySelector(".duplicate-group-preview-btn");
      return btn && !btn.disabled;
    },
    { timeout: 45000 },
  );

  await page.locator(".duplicate-group-preview-btn").click();
  await page.waitForSelector(".merge-confirm-modal", { timeout: 10000 });
  await page.locator(".modal footer .btn.danger").last().click();

  await page.waitForFunction(
    () => document.querySelector(".duplicate-groups-table"),
    { timeout: 90000 },
  );

  await browser.close();

  assert(
    mergeExecuteStatuses.some((s) => s === 200),
    `merge-execute statuses: ${mergeExecuteStatuses.join(",")}`,
  );

  const enc = encodeURIComponent(groupKey);
  const after = await apiGet(
    `/api/v1/admin/data-operations/runs/${RUN_ID}/dataset/duplicate-groups?search=${encodeURIComponent(GROUP_SEARCH)}&page=1&page_size=5`,
  );
  const stillListed = (after.json?.items ?? []).some((i) => i.group_key === groupKey);

  console.log(
    JSON.stringify(
      {
        runId: RUN_ID,
        groupKey,
        mergeExecuteStatuses,
        groupStillInList: stillListed,
        UI_TEST: stillListed ? "FAIL" : "PASS",
      },
      null,
      2,
    ),
  );
  if (stillListed) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  console.log(JSON.stringify({ UI_TEST: "FAIL", error: String(err) }));
  process.exit(1);
});
