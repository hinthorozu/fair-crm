/**
 * Dirty-form browser acceptance for representative surfaces:
 * - modal (Customer create)
 * - todo modal
 * - page/wizard (Scraper operation wizard)
 *
 * Usage:
 *   VITE_DEV_BYPASS_ENABLED=true npm run dev -- --host 127.0.0.1 --port 5175
 *   node scripts/dirty-form-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5175";
const UNSAVED = "Kaydedilmemiş değişiklikler var. Çıkmak istediğinize emin misiniz?";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForApp(page) {
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(800);
}

async function openCustomerCreateModal(page) {
  await page.goto(`${BASE}/customers`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(600);
  await page.getByRole("button", { name: /Yeni Müşteri/i }).first().click();
  await page.waitForSelector('[role="dialog"]', { timeout: 15000 });
}

async function fillCustomerName(page, value) {
  await page.locator("#customer-display-name").fill(value);
}

async function clickModalClose(page) {
  // Header IconButton is the first button in dialog header.
  await page.locator('[role="dialog"] .modal-header button').first().click();
}

async function expectUnsavedConfirm(page, visible) {
  const text = page.getByText(UNSAVED);
  if (visible) {
    await text.waitFor({ state: "visible", timeout: 5000 });
  } else {
    await page.waitForTimeout(250);
    assert((await text.count()) === 0, "Unexpected unsaved confirm");
  }
}

async function clickConfirmAction(page, label) {
  // Nested confirm can sit above modal; force avoids accidental page-content intercepts.
  await page.getByRole("button", { name: label, exact: true }).click({ force: true });
}

async function clickSidebar(page, name) {
  // Modal backdrop blocks normal pointer clicks; dispatch a cancelable click on the nav link
  // so React handleNav + dirty gate still run (Playwright force:true is unreliable here).
  const pattern = name instanceof RegExp ? name.source : String(name);
  const clicked = await page.evaluate((source) => {
    const re = new RegExp(source, "i");
    const link = Array.from(document.querySelectorAll("a.sidebar-link")).find((a) =>
      re.test(a.textContent || ""),
    );
    if (!link) return false;
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    return true;
  }, pattern);
  assert(clicked, `Sidebar link not found for ${pattern}`);
}

async function runModalAcceptance(page, results) {
  // 1 clean → exit → no warn
  await openCustomerCreateModal(page);
  await clickModalClose(page);
  await expectUnsavedConfirm(page, false);
  assert((await page.locator('[role="dialog"]').count()) === 0, "Clean modal should close");
  results.push("modal clean close: PASS");

  // 2 dirty → exit → warn
  await openCustomerCreateModal(page);
  await fillCustomerName(page, "Dirty Test Co");
  await clickModalClose(page);
  await expectUnsavedConfirm(page, true);
  results.push("modal dirty warn: PASS");

  // 3 Forma Dön → form open + data kept
  await clickConfirmAction(page, "Forma Dön");
  await expectUnsavedConfirm(page, false);
  assert((await page.locator('[role="dialog"]').count()) > 0, "Form should stay open");
  const value = await page.locator("#customer-display-name").inputValue();
  assert(value.includes("Dirty Test Co"), `Value preserved, got: ${value}`);
  results.push("modal Forma Dön: PASS");

  // 5 revert → dirty false
  await fillCustomerName(page, "");
  await clickModalClose(page);
  await expectUnsavedConfirm(page, false);
  assert((await page.locator('[role="dialog"]').count()) === 0, "Reverted form should close clean");
  results.push("modal revert clean: PASS");

  // 4 Çık discards
  await openCustomerCreateModal(page);
  await fillCustomerName(page, "Discard Me");
  await clickModalClose(page);
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Çık");
  await expectUnsavedConfirm(page, false);
  assert((await page.locator('[role="dialog"]').count()) === 0, "Discard should close modal");
  results.push("modal Çık discard: PASS");

  // 7 sidebar while dirty (force through backdrop)
  await openCustomerCreateModal(page);
  await fillCustomerName(page, "Nav Block");
  await clickSidebar(page, /Dashboard/i);
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Forma Dön");
  assert(page.url().includes("/customers"), "Should stay on customers after Forma Dön");
  const kept = await page.locator("#customer-display-name").inputValue();
  assert(kept.includes("Nav Block"), "Dirty value kept after Forma Dön from nav");
  await clickSidebar(page, /Dashboard/i);
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Çık");
  await page.waitForTimeout(400);
  assert(page.url().includes("/dashboard"), `Expected dashboard after discard, got ${page.url()}`);
  results.push("modal sidebar nav guard: PASS");

  // 7b browser back while dirty (must stay in SPA history — no full page.goto)
  await clickSidebar(page, /Dashboard/i);
  await page.waitForTimeout(300);
  await clickSidebar(page, /Müşteriler/i);
  await page.waitForTimeout(500);
  await page.getByRole("button", { name: /Yeni Müşteri/i }).first().click();
  await page.waitForSelector('[role="dialog"]', { timeout: 15000 });
  await fillCustomerName(page, "Back Block");
  await page.waitForTimeout(200);
  await page.goBack();
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Forma Dön");
  assert(page.url().includes("/customers"), "Browser back Forma Dön stays");
  await page.goBack();
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Çık");
  results.push("modal browser back guard: PASS");
}

async function runWizardAcceptance(page, results) {
  await page.goto(`${BASE}/operations/new/scraper`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1000);

  const cancel = page.getByRole("button", { name: /İptal|Vazgeç/i }).first();
  if ((await cancel.count()) === 0) {
    results.push("wizard: SKIP (cancel button not found)");
    return;
  }

  // clean cancel
  await cancel.click();
  await expectUnsavedConfirm(page, false);
  results.push("wizard clean leave: PASS");

  await page.goto(`${BASE}/operations/new/scraper`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1000);
  const select = page.locator("#scraper-wizard-adapter, select").first();
  if ((await select.count()) === 0) {
    results.push("wizard dirty: SKIP (no select)");
    return;
  }
  const optionCount = await select.locator("option").count();
  if (optionCount < 2) {
    results.push("wizard dirty: SKIP (no adapters)");
    return;
  }
  await select.selectOption({ index: 1 });
  await cancel.click();
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Forma Dön");
  assert(page.url().includes("/operations/new/scraper"), "Wizard should remain");
  const selected = await select.inputValue();
  assert(Boolean(selected), "Wizard selection preserved");
  results.push("wizard dirty Forma Dön: PASS");

  await clickSidebar(page, /Otomasyonlar|Dashboard/i);
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Çık");
  results.push("wizard sidebar discard: PASS");
}

async function runTodoModalAcceptance(page, results) {
  await page.goto(`${BASE}/todos`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(800);
  const newBtn = page.getByRole("button", { name: /Yeni Görev/i }).first();
  if ((await newBtn.count()) === 0) {
    results.push("todo modal: SKIP (new button not found)");
    return;
  }
  await newBtn.click();
  await page.waitForSelector('[role="dialog"]', { timeout: 15000 });
  await page.locator("#todo-title").fill("Dirty Todo");
  await page.getByRole("button", { name: /İptal|Vazgeç/i }).first().click();
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Forma Dön");
  const kept = await page.locator("#todo-title").inputValue();
  assert(kept === "Dirty Todo", "Todo title preserved");
  await page.getByRole("button", { name: /İptal|Vazgeç/i }).first().click();
  await expectUnsavedConfirm(page, true);
  await clickConfirmAction(page, "Çık");
  results.push("todo modal dirty cancel: PASS");
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];

  try {
    await waitForApp(page);
    await runModalAcceptance(page, results);
    await runTodoModalAcceptance(page, results);
    await runWizardAcceptance(page, results);
    console.log("DIRTY FORM ACCEPTANCE RESULTS");
    for (const line of results) console.log(`- ${line}`);
    const failed = results.some((line) => line.includes("FAIL"));
    if (failed) process.exitCode = 1;
  } catch (err) {
    console.error("ACCEPTANCE FAILED:", err);
    console.log("PARTIAL RESULTS");
    for (const line of results) console.log(`- ${line}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await main();
