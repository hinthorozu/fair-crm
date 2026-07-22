/**
 * Runtime smoke: open Import Wizard continue/decisions route and assert
 * `decisionBusy is not defined` does not appear in page/console errors.
 *
 * Uses mocked /api responses so verification does not need a live login password.
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const BATCH_ID = "11111111-1111-4111-8111-111111111111";
const FAIR_ID = "22222222-2222-4222-8222-222222222222";
const ROW_ID = "33333333-3333-4333-8333-333333333333";

const batch = {
  id: BATCH_ID,
  fair_id: FAIR_ID,
  status: "decision_required",
  filename: "smoke.xlsx",
  created_rows: 0,
  updated_rows: 0,
  skipped_rows: 0,
  failed_rows: 0,
  total_rows: 1,
  available_sheets: ["Sheet1"],
  selected_sheet_name: "Sheet1",
  header_mode: "first_row_header",
  header_row_index: 0,
  column_mapping_json: { company_name: { value: 0 } },
};

const row = {
  id: ROW_ID,
  batch_id: BATCH_ID,
  row_number: 1,
  status: "ready_to_create",
  decision: null,
  match_customer_id: null,
  match_confidence: null,
  normalized_data_json: { company_name: "Smoke Co" },
  validation_errors_json: [],
  raw_data_json: {},
};

const pageErrors = [];
const consoleErrors = [];

function json(data, status = 200) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify(data),
  };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on("pageerror", (err) => pageErrors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      "fair-crm.auth.session",
      JSON.stringify({
        accessToken: "smoke-session",
        organizationId: "00000000-0000-4000-8000-000000000010",
        email: "smoke@local.test",
      }),
    );
  });

  // Only mock backend JSON APIs — never Vite modules under /src/api/.
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();

    if (path.includes(`/imports/${BATCH_ID}/rows`) && method === "GET") {
      return route.fulfill(
        json({
          items: [row],
          pagination: {
            page: 1,
            pageSize: 25,
            totalItems: 1,
            totalPages: 1,
          },
          filter_counts: { pending: 1, all: 1 },
        }),
      );
    }
    if (path.endsWith(`/imports/${BATCH_ID}`) && method === "GET") {
      return route.fulfill(json(batch));
    }
    if (path.includes(`/imports/${BATCH_ID}/mapping-preview`)) {
      return route.fulfill(
        json({
          columns: [],
          grid: { columns: [], rows: [], total_data_rows: 1, preview_row_count: 0 },
        }),
      );
    }
    if (path.includes(`/fairs/${FAIR_ID}`) && method === "GET") {
      return route.fulfill(
        json({
          id: FAIR_ID,
          name: "Smoke Fair",
          status: "active",
        }),
      );
    }
    if (path.includes("/participations") && method === "GET") {
      return route.fulfill(
        json({
          items: [],
          pagination: { page: 1, pageSize: 1, totalItems: 0, totalPages: 0 },
        }),
      );
    }
    if (path.includes("/imports") && method === "GET") {
      return route.fulfill(
        json({
          items: [batch],
          pagination: { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 },
        }),
      );
    }
    // Keep auth/session alive for unrelated calls.
    return route.fulfill(json({ ok: true }));
  });

  // 1) Import list route
  await page.goto(`${BASE}/data-integration/imports`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);
  const listText = await page.locator("body").innerText();
  const listOk =
    !listText.includes("decisionBusy is not defined") &&
    (listText.includes("Import") || listText.includes("İçe Aktar") || listText.includes("Veri"));

  // 2) Continue / decisions route (the failing path)
  await page.goto(`${BASE}/data-integration/imports/continue/${BATCH_ID}`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForTimeout(2000);

  const bodyText = await page.locator("body").innerText();
  const onLogin = /Giriş Yap/.test(bodyText) && !/Karar|Smoke Co|merge-preview/.test(bodyText);
  const hasDecisionUi =
    (await page.locator(".merge-preview-list, .bulk-decision-panel, .merge-preview-item").count()) > 0 ||
    bodyText.includes("Smoke Co") ||
    /Karar/.test(bodyText);

  const decisionBusyError = [...pageErrors, ...consoleErrors].some((msg) =>
    /decisionBusy is not defined/i.test(msg),
  );

  await browser.close();

  const result = {
    listUrl: `${BASE}/data-integration/imports`,
    decisionUrl: `${BASE}/data-integration/imports/continue/${BATCH_ID}`,
    listOk,
    onLogin,
    hasDecisionUi,
    decisionBusyError,
    pageErrors,
    consoleErrors,
    bodyPreview: bodyText.slice(0, 500),
  };
  console.log(JSON.stringify(result, null, 2));

  if (onLogin) {
    process.exitCode = 2;
    return;
  }
  if (decisionBusyError) {
    process.exitCode = 1;
    return;
  }
  if (!hasDecisionUi || !listOk) {
    process.exitCode = 3;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
