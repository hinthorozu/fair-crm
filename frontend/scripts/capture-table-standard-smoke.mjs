/**
 * DEV visual proof for width-responsive table standard.
 * Usage: node scripts/capture-table-standard-smoke.mjs
 * Requires: frontend on http://127.0.0.1:5173
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(
  __dirname,
  "../../scripts/maintenance/reports/table-standard-smoke",
);
const base = "http://127.0.0.1:5173/dev/table-standard-smoke";

fs.mkdirSync(outDir, { recursive: true });

async function shot(page, name) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: true });
  console.log("wrote", file);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

await page.goto(`${base}?tab=customers`, { waitUntil: "networkidle" });
await shot(page, "01-customers-wide.png");

await page.setViewportSize({ width: 720, height: 900 });
await page.waitForTimeout(400);
await shot(page, "02-customers-narrow.png");

await page.locator("button.table-expand-btn").first().click();
await page.waitForTimeout(200);
await shot(page, "03-customers-child-open.png");

await page.locator(".server-data-table-bottom-pagination button", { hasText: "Sonraki" }).click();
await page.waitForTimeout(200);
await shot(page, "04-pagination-sync-page2.png");

await page.goto(`${base}?tab=fairs`, { waitUntil: "networkidle" });
await page.setViewportSize({ width: 720, height: 900 });
await page.waitForTimeout(400);
await shot(page, "05-fairs-narrow.png");
await page.locator("button.table-expand-btn").first().click();
await page.waitForTimeout(200);
await shot(page, "06-fairs-child-open.png");

await page.goto(`${base}?tab=todos`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await shot(page, "07-todos-dual-pagination.png");
await page.locator("button.table-expand-btn").first().click();
await page.waitForTimeout(200);
await shot(page, "08-todos-child-open.png");

await page.goto(`${base}?tab=imports`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await page.locator("button.table-expand-btn").first().click();
await page.waitForTimeout(200);
await shot(page, "09-imports-dual-child-open.png");

await page.goto(`${base}?tab=admin`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await page.locator("button.table-expand-btn").first().click();
await page.waitForTimeout(200);
await shot(page, "10-admin-dual-child-open.png");

await browser.close();
console.log("done", outDir);
