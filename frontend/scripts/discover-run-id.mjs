import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5175";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const seen = [];
page.on("response", async (res) => {
  const url = res.url();
  if (!url.includes("/api/v1/scraper/runs")) return;
  try {
    const json = await res.json();
    seen.push({ url, json });
  } catch {
    /* ignore */
  }
});

await page.goto(`${BASE}/data-integration/run-history`, {
  waitUntil: "networkidle",
  timeout: 60000,
});
await page.waitForTimeout(1500);

let runId = null;
for (const item of seen) {
  const body = item.json;
  const first = body?.items?.[0] || body?.data?.[0] || body?.[0];
  if (first?.id) {
    runId = first.id;
    break;
  }
  if (first?.run_id) {
    runId = first.run_id;
    break;
  }
}

// Fallback: adapter detail runs tab + force click
if (!runId) {
  await page.goto(`${BASE}/data-integration/adapters/customer_contact_enrichment?tab=runs`, {
    waitUntil: "networkidle",
    timeout: 60000,
  });
  await page.waitForTimeout(1200);
  for (const item of seen) {
    const body = item.json;
    const first = body?.items?.[0] || body?.data?.[0];
    if (first?.id || first?.run_id) {
      runId = first.id || first.run_id;
      break;
    }
  }
  const btn = page.locator("button.btn.link", { hasText: /\d{2}\.\d{2}\.\d{4}/ }).first();
  if ((await btn.count()) > 0) {
    await btn.click({ force: true });
    await page.waitForTimeout(1500);
    console.log("after_force_click", page.url());
    const m = page.url().match(/\/runs\/([^/?#]+)/);
    if (m) runId = decodeURIComponent(m[1]);
  }
}

console.log(JSON.stringify({ runId, seenCount: seen.length }, null, 2));
await browser.close();
if (!runId) process.exit(1);
