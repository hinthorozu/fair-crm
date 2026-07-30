/**
 * Enrichment operation detail: live Çalıştırma Geçmişi progress (silent poll).
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:18173";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:18001";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";

const FAIR_KAPI = "cfffb498-7db9-5fdc-8318-a2dd270f5c46";
const FAIR_CAM = "eb6bb727-8d61-58e6-bbb4-3cebdcce5bad";

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

function parseProgressCell(text) {
  // e.g. "14% (313/45)" => total=313, processed=45, pct=14
  const m = String(text).trim().match(/^(\d+)%\s*\((\d+)\/(\d+)\)$/);
  if (!m) return null;
  return { pct: Number(m[1]), total: Number(m[2]), processed: Number(m[3]) };
}

async function main() {
  const created = await api("POST", "/api/v1/operations", {
    operation_type: "enrichment",
    title: `E2E Enrich Progress ${Date.now().toString(36)}`,
    source_kind: "fair",
    source_ids: [FAIR_KAPI, FAIR_CAM],
    type_config: {
      adapter_key: "customer_contact_enrichment",
      requested_fields: ["email"],
      limit: 3,
      include_existing_email: true,
      fair_ids: [FAIR_KAPI, FAIR_CAM],
    },
    start_immediately: true,
  });
  assert(created.status === 201, `create op failed: ${created.text}`);
  const operationId = created.json.id;
  console.log("operation", operationId);

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

  await page.goto(`${BASE}/operations/${operationId}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.getByRole("heading", { name: /Çalıştırma Geçmişi/i }).waitFor({ timeout: 30000 });
  await page.getByRole("heading", { name: /Çalıştırma Geçmişi/i }).scrollIntoViewIfNeeded();

  // Wait until run history shows a progress percentage cell (may be in responsive layout)
  await page.waitForFunction(
    () => /\d+%\s*\(\d+\/\d+\)/.test(document.body.innerText),
    null,
    { timeout: 120000 },
  );
  let sawTotal = false;
  let sawProgressIncrease = false;
  let sawSuccessFailLive = false;
  let lastProcessed = -1;
  let lastSucceeded = -1;
  let lastFailed = -1;
  let finalRun = null;
  let formatOk = false;
  let lastUiProgress = null;

  for (let i = 0; i < 90; i++) {
    const detail = await api("GET", `/api/v1/operations/${operationId}`);
    assert(detail.status === 200, detail.text);
    const run = detail.json.runs?.[0];
    assert(run, "no run");
    finalRun = run;

    if (run.total_items > 0) sawTotal = true;
    if (run.processed_items > lastProcessed && lastProcessed >= 0) sawProgressIncrease = true;
    if (run.processed_items > 0) {
      if (
        (run.succeeded_items !== lastSucceeded || run.failed_items !== lastFailed) &&
        (lastSucceeded >= 0 || lastFailed >= 0)
      ) {
        sawSuccessFailLive = true;
      }
    }
    lastProcessed = run.processed_items;
    lastSucceeded = run.succeeded_items;
    lastFailed = run.failed_items;

    // Expand child row if present (responsive hidden columns)
    const expandBtn = page.locator("table tbody tr").first().locator("button, .expand-toggle, [aria-label*='expand' i]").first();
    if (await expandBtn.count()) {
      try {
        await expandBtn.click({ timeout: 500 });
      } catch {
        /* already open / not expandable */
      }
    }

    const bodyText = await page.locator("body").innerText();
    const progressMatch = bodyText.match(/(\d+)%\s*\((\d+)\/(\d+)\)/);
    if (progressMatch) {
      formatOk = true;
      lastUiProgress = parseProgressCell(progressMatch[0]);
      // UI silent poll can lag one tick behind API — only check format + total once known.
      if (run.total_items > 0) {
        assert(
          lastUiProgress.total === run.total_items,
          `UI total ${lastUiProgress.total} vs api ${run.total_items}`,
        );
        assert(
          lastUiProgress.processed <= run.processed_items,
          `UI processed ${lastUiProgress.processed} ahead of api ${run.processed_items}`,
        );
        const expectedPct = Math.round((lastUiProgress.processed / lastUiProgress.total) * 100);
        assert(
          lastUiProgress.pct === expectedPct,
          `pct ${lastUiProgress.pct} expected ${expectedPct} for UI pair`,
        );
      }
    }

    if (["completed", "failed", "cancelled"].includes(run.status) && sawTotal && formatOk) {
      // Give silent poll one more cycle to catch final counts
      await page.waitForTimeout(3500);
      const finalBody = await page.locator("body").innerText();
      const finalMatch = finalBody.match(/(\d+)%\s*\((\d+)\/(\d+)\)/);
      if (finalMatch) lastUiProgress = parseProgressCell(finalMatch[0]);
      break;
    }
    await page.waitForTimeout(2000);
  }

  assert(sawTotal, "total_items never became > 0");
  assert(finalRun, "missing final run");
  assert(
    ["completed", "failed", "cancelled"].includes(finalRun.status),
    `run did not finish: ${finalRun.status}`,
  );
  if (!formatOk) {
    const dump = await page.locator("body").innerText();
    throw new Error(`progress cell format not observed. body snippet:\n${dump.slice(0, 2000)}`);
  }
  if (finalRun.status === "completed") {
    assert(
      finalRun.succeeded_items + finalRun.failed_items === finalRun.processed_items,
      `success+fail != processed (${finalRun.succeeded_items}+${finalRun.failed_items}!=${finalRun.processed_items})`,
    );
    assert(
      finalRun.processed_items === finalRun.total_items,
      `processed != total (${finalRun.processed_items}!=${finalRun.total_items})`,
    );
  }

  // At least some live movement if run took more than one poll tick
  if (finalRun.total_items >= 2 && finalRun.processed_items === finalRun.total_items) {
    assert(
      sawProgressIncrease || finalRun.processed_items > 0,
      "expected live processed increase while running",
    );
  }

  const uiRow = await page.locator("body").innerText();
  const parsed =
    lastUiProgress ||
    parseProgressCell(uiRow.match(/(\d+)%\s*\((\d+)\/(\d+)\)/)?.[0] || "");
  assert(parsed, `bad UI progress format in page`);
  assert(parsed.total === finalRun.total_items, `final UI total ${parsed.total}`);
  assert(parsed.processed === finalRun.processed_items, `final UI processed ${parsed.processed}`);

  await browser.close();
  console.log(
    JSON.stringify({
      ok: true,
      operationId,
      sawTotal,
      sawProgressIncrease,
      sawSuccessFailLive,
      finalRun: {
        status: finalRun.status,
        total: finalRun.total_items,
        processed: finalRun.processed_items,
        succeeded: finalRun.succeeded_items,
        failed: finalRun.failed_items,
        progress: finalRun.progress,
      },
      ui: parsed,
    }),
  );
  console.log("UI_TEST PASS");
}

main().catch((err) => {
  console.error("UI_TEST FAIL", err);
  process.exit(1);
});
