/**
 * Duplicate Customer Analysis: FairEntitySelect + merge flow (real browser).
 *
 *   Backend dev-bypass on FAIR_CRM_API_BASE (default 54960)
 *   VITE_DEV_BYPASS_ENABLED=true when starting Vite (e2e config)
 *   node scripts/duplicate-merge-fair-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:54961";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:54960";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";

const REPRO_RUN_ID = process.env.DUP_MERGE_RUN_ID || "07bc9e90-94e9-4412-876b-2b1cb6bef816";
const REPRO_GROUP_KEY =
  process.env.DUP_MERGE_GROUP_KEY || "agrozan tarim urunleri gida urunleri";

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

async function waitForRunSuccess(runId) {
  for (let i = 0; i < 40; i++) {
    const run = await api("GET", `/api/v1/admin/data-operations/runs/${runId}`);
    if (run.json?.result === "success") return run.json;
    if (run.json?.result === "failed") throw new Error(`run failed: ${run.text}`);
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("run timed out");
}

async function seedEmailDuplicateGroup(stamp) {
  const email = `dup-merge-e2e-${stamp}@example.com`;
  const mk = async (name) => {
    const res = await api("POST", "/api/v1/customers", {
      display_name: name,
      email,
      status: "active",
    });
    assert(res.status === 201, `customer create failed: ${res.text}`);
    return res.json.id;
  };
  await mk(`Dup Merge A ${stamp}`);
  await mk(`Dup Merge B ${stamp}`);

  const runRes = await api("POST", "/api/v1/admin/data-operations/duplicate_customer_analysis/run", {
    group_by: "email",
  });
  assert(runRes.status === 202, `analysis run failed: ${runRes.text}`);
  await waitForRunSuccess(runRes.json.id);

  const groups = await api(
    "GET",
    `/api/v1/admin/data-operations/runs/${runRes.json.id}/dataset/duplicate-groups?search=${encodeURIComponent(email)}&page=1&page_size=5`,
  );
  assert(groups.status === 200 && groups.json?.items?.length >= 1, "duplicate group missing");
  return { runId: runRes.json.id, groupKey: groups.json.items[0].group_key };
}

async function runMergeFlow(page, runId, groupKey, mergePreviewOk, mergeExecuteOk) {
  const groupParam = encodeURIComponent(groupKey).replace(/%20/g, "+");
  const detailUrl = `${BASE}/operations/duplicate-check/runs/${runId}?operation=duplicate_customer_analysis&group=${groupParam}`;
  await page.goto(detailUrl, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);

  await page.waitForSelector(".duplicate-group-customer-card", { timeout: 20000 });
  const customerCards = await page.locator(".duplicate-group-customer-card").count();
  assert(customerCards >= 2, `expected >=2 customers, got ${customerCards}`);

  try {
    await page.waitForFunction(
      () => {
        const btn = document.querySelector(".duplicate-group-preview-btn");
        return btn && !btn.disabled;
      },
      { timeout: 30000 },
    );
  } catch {
    const previewErr = await page.locator(".duplicate-group-summary-validation").allTextContents();
    const loadingText = await page.locator(".duplicate-group-merge-summary-loading").allTextContents();
    throw new Error(
      `merge button stayed disabled. previews=${mergePreviewOk.join(",")} loading=${loadingText.join("|")} err=${previewErr.join("|")}`,
    );
  }

  assert(mergePreviewOk.some((s) => s === 200), `merge-preview failed: ${mergePreviewOk.join(",")}`);

  await page.locator(".duplicate-group-preview-btn").click();
  await page.waitForSelector(".merge-confirm-modal", { timeout: 8000 });
  await page.locator(".modal footer .btn.danger, .modal .btn.danger").last().click();

  await page.waitForFunction(
    () => document.querySelector(".duplicate-groups-table"),
    { timeout: 60000 },
  );

  assert(
    mergeExecuteOk.some((s) => s === 200),
    `merge-execute failed: ${mergeExecuteOk.join(",")}`,
  );
}

async function main() {
  const results = {
    dropdown: false,
    reproPreview: false,
    reproExecuteNote: "",
    mergeCleanData: false,
    errors: [],
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on("console", (msg) => {
    if (msg.type() === "error") results.errors.push(`console: ${msg.text()}`);
  });

  const mergePreviewOk = [];
  const mergeExecuteOk = [];
  page.on("response", (res) => {
    const url = res.url();
    if (url.includes("/merge-preview")) mergePreviewOk.push(res.status());
    if (url.includes("/merge-execute")) mergeExecuteOk.push(res.status());
  });

  try {
    await page.goto(`${BASE}/operations/new/duplicate-check`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);

    const fairInput = page.locator("#duplicate-fair-filter");
    await fairInput.click();
    await page.waitForSelector(".entity-select-dropdown", { timeout: 8000 });
    const clearLabel = page.locator(".entity-select-dropdown .entity-select-option").first();
    assert((await clearLabel.innerText()).includes("Tüm Fuarlar"), "Tüm Fuarlar clear option missing");

    await fairInput.fill("inter");
    await page.waitForTimeout(500);
    const interOption = page
      .locator(".entity-select-option-label")
      .filter({ hasText: /intermob/i })
      .first();
    assert((await interOption.count()) > 0, "Intermob fair option not found");
    await interOption.click();
    await page.waitForTimeout(400);

    await fairInput.click();
    await page.keyboard.press("ArrowDown");
    await page.waitForSelector(".entity-select-dropdown", { timeout: 8000 });
    await page.locator(".entity-select-dropdown .entity-select-option").first().click();
    results.dropdown = true;

    mergePreviewOk.length = 0;
    mergeExecuteOk.length = 0;
    const groupParam = encodeURIComponent(REPRO_GROUP_KEY).replace(/%20/g, "+");
    await page.goto(
      `${BASE}/operations/duplicate-check/runs/${REPRO_RUN_ID}?operation=duplicate_customer_analysis&group=${groupParam}`,
      { waitUntil: "networkidle" },
    );
    await page.waitForSelector(".duplicate-group-customer-card", { timeout: 20000 });
    await page.waitForTimeout(2000);
    results.reproPreview = mergePreviewOk.some((s) => s === 200);
    if (mergeExecuteOk.length > 0) {
      results.reproExecuteNote = `execute statuses: ${mergeExecuteOk.join(",")}`;
    } else {
      const enabled = await page.locator(".duplicate-group-preview-btn").isEnabled();
      results.reproExecuteNote = enabled
        ? "repro: preview ok, merge button enabled (execute not attempted in repro step)"
        : "repro: merge button still disabled";
    }

    mergePreviewOk.length = 0;
    mergeExecuteOk.length = 0;
    const seed = await seedEmailDuplicateGroup(Date.now());
    await runMergeFlow(page, seed.runId, seed.groupKey, mergePreviewOk, mergeExecuteOk);
    results.mergeCleanData = true;
  } finally {
    await browser.close();
  }

  const pass = results.dropdown && results.reproPreview && results.mergeCleanData;
  console.log(JSON.stringify({ ...results, UI_TEST: pass ? "PASS" : "FAIL" }, null, 2));
  if (!pass) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
