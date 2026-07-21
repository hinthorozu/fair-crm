import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const seen = [];
page.on("response", async (res) => {
  const url = res.url();
  if (!/import|batch/i.test(url)) return;
  try {
    const json = await res.json();
    seen.push({ url, json });
  } catch {
    /* ignore */
  }
});

await page.goto(`${BASE}/data-integration/imports`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1500);

let batchId = null;
for (const item of seen) {
  const body = item.json;
  const list = body?.items || body?.data || body?.batches || (Array.isArray(body) ? body : null);
  const first = Array.isArray(list) ? list[0] : null;
  if (first?.id) {
    batchId = first.id;
    break;
  }
  if (first?.batch_id) {
    batchId = first.batch_id;
    break;
  }
}

console.log(JSON.stringify({ batchId, urls: seen.map((s) => s.url).slice(0, 10) }, null, 2));
await browser.close();
if (!batchId) process.exit(1);
