/**
 * Import İşleri: analiz geçmişi + stale batch yeniden analiz (gerçek API + browser).
 *
 * Prerequisites:
 *   Backend: FAIR_CRM_DEV_BYPASS_CORE=true APP_ENV=development uvicorn on FAIR_CRM_API_BASE
 *   Frontend: VITE_DEV_BYPASS_ENABLED=true on FAIR_CRM_BASE_URL
 *
 *   node scripts/import-reanalyze-stale-acceptance.mjs
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

async function waitAnalyze(batchId) {
  const start = await api("POST", `/api/v1/data-integration/imports/${batchId}/analyze-job`);
  assert(start.status === 202, `analyze start failed ${start.status} ${start.text}`);
  const jobId = start.json.job_id;
  for (let i = 0; i < 90; i++) {
    const job = await api("GET", `/api/v1/data-integration/jobs/${jobId}`);
    assert(job.status === 200, `job poll failed ${job.status}`);
    if (job.json.status === "completed") return;
    if (job.json.status === "failed") {
      throw new Error(job.json.error_message || "analyze job failed");
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("analyze job timeout");
}

async function createFair(name) {
  const res = await api("POST", "/api/v1/fairs", {
    name,
    location: "Istanbul",
    start_date: "2026-06-01",
    end_date: "2026-06-03",
  });
  assert(res.status === 201, `fair create failed ${res.status}`);
  return res.json.id;
}

async function createCanonicalBatch(fairId, runSuffix, companyName) {
  const runId = crypto.randomUUID();
  const res = await api("POST", "/api/v1/data-integration/imports/from-canonical", {
    source: {
      type: "scraper",
      adapter_key: "tuyap_new",
      fair_id: fairId,
      run_id: runId,
      source_url: `https://e2e.test/${runSuffix}`,
    },
    metadata: {
      created_at: new Date().toISOString(),
      row_count: 1,
    },
    rows: [
      {
        company_name: companyName,
        normalized_company_name: companyName.toLowerCase(),
        emails: [],
        phones: [],
        country: "Türkiye",
        raw: {},
      },
    ],
  });
  assert(res.status === 201, `canonical batch failed ${res.status} ${res.text}`);
  return res.json.batch.id;
}

async function applyCreateNew(batchId) {
  const rows = await api("GET", `/api/v1/data-integration/imports/${batchId}/rows?page_size=25`);
  assert(rows.status === 200, "rows list failed");
  const rowId = rows.json.items[0].id;
  const decision = await api("PATCH", `/api/v1/data-integration/imports/${batchId}/rows/${rowId}/decision`, {
    decision: "create_new",
  });
  assert(decision.status === 200, "decision failed");
  const apply = await api("POST", `/api/v1/data-integration/imports/${batchId}/decisions/apply`, {
    row_ids: [rowId],
  });
  assert(apply.status === 200, `apply failed ${apply.status} ${apply.text}`);
}

async function main() {
  const companyName = `E2E-STALE-${crypto.randomUUID()}`;
  const fairOne = await createFair(`E2E ABC Fair One ${Date.now()}`);
  const fairTwo = await createFair(`E2E ABC Fair Two ${Date.now()}`);
  const batchOne = await createCanonicalBatch(fairOne, "b1", companyName);
  const batchTwo = await createCanonicalBatch(fairTwo, "b2", companyName);

  await waitAnalyze(batchTwo);
  let rowsTwo = await api("GET", `/api/v1/data-integration/imports/${batchTwo}/rows?page_size=25`);
  assert(
    rowsTwo.json.items[0].status === "ready_to_create",
    `batch2 should be new before batch1 apply, got ${rowsTwo.json.items[0].status}`,
  );

  await waitAnalyze(batchOne);
  await applyCreateNew(batchOne);

  const batchTwoDetail = await api("GET", `/api/v1/data-integration/imports/${batchTwo}`);
  assert(batchTwoDetail.json.analyzed_at, "analyzed_at should be set before UI");
  const fileName = batchTwoDetail.json.file_name;

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1600, height: 900 });

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

  await page.goto(`${BASE}/data-integration/imports`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.getByRole("heading", { name: /Import İşleri/i }).waitFor({ timeout: 30000 });
  assert(!page.url().includes("/login"), "expected dev bypass to skip login");

  const rowLocator = page.locator("tbody tr:visible").filter({ hasText: fileName });
  await rowLocator.first().waitFor({ state: "visible", timeout: 20000 });

  const rowText = await rowLocator.first().innerText();
  assert(rowText.includes("Analiz Edildi"), "list should show Analiz Edildi");
  assert(rowText.includes("Karar Bekliyor"), "status column unchanged");
  assert(
    (await rowLocator.getByRole("button", { name: "Yeniden Analiz Et" }).count()) > 0,
    "reanalyze button missing",
  );

  const skeletonBefore = await page.locator(".table-skeleton, [data-testid='table-skeleton']").count();
  const rowCountBefore = await page.locator("tbody tr").count();

  await rowLocator.getByRole("button", { name: "Yeniden Analiz Et" }).click();

  for (let i = 0; i < 120; i++) {
    const running = await rowLocator.getByRole("button", { name: /Yeniden analiz/i }).count();
    if (running === 0) break;
    const skeletonMid = await page.locator(".table-skeleton, [data-testid='table-skeleton']").count();
    assert(skeletonMid === skeletonBefore, "table skeleton appeared during reanalyze refresh");
    const rowCountMid = await page.locator("tbody tr").count();
    assert(rowCountMid >= rowCountBefore, "table rows disappeared during reanalyze");
    await page.waitForTimeout(500);
  }

  await page.waitForTimeout(800);
  const rowsTwoAfter = await api("GET", `/api/v1/data-integration/imports/${batchTwo}/rows?page_size=25`);
  assert(rowsTwoAfter.json.items[0].status === "ready_to_update", "ABC should match CRM after reanalyze");
  assert(rowsTwoAfter.json.items[0].match_customer_id, "match_customer_id required");

  const batchTwoDetailAfter = await api("GET", `/api/v1/data-integration/imports/${batchTwo}`);
  assert(batchTwoDetailAfter.json.analyzed_at, "analyzed_at should be set");

  await browser.close();
  console.log("UI_TEST: PASS");
  console.log("batch_one", batchOne);
  console.log("batch_two", batchTwo);
}

main().catch((err) => {
  console.error("UI_TEST: FAIL");
  console.error(err);
  process.exit(1);
});
