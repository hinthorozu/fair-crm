/**
 * Remaining dirty-form acceptance with real JWT (no bypass).
 *
 * Usage (frontend/):
 *   $env:DEV_USER_PASSWORD='...'
 *   node scripts/dirty-form-remaining-acceptance.mjs
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const EMAIL = process.env.FAIR_CRM_DEV_EMAIL || "dev@example.com";
const PASSWORD = process.env.DEV_USER_PASSWORD || process.env.FAIR_CRM_DEV_PASSWORD;
const UNSAVED = "Kaydedilmemiş değişiklikler var. Çıkmak istediğinize emin misiniz?";
const XLSX = path.join(__dirname, "_dirty_accept_sample.xlsx");

if (!PASSWORD) {
  console.error("DEV_USER_PASSWORD or FAIR_CRM_DEV_PASSWORD required");
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.fill("#login-email, input[type='email']", EMAIL);
  await page.fill("#login-password, input[type='password']", PASSWORD);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30000 }),
    page.click('button[type="submit"]'),
  ]);
  const session = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  assert(session?.accessToken, "LOGIN_FAIL: no JWT accessToken in localStorage");
  console.log("login_ok jwt_present=true");
  return session.accessToken;
}

async function expectUnsaved(page, visible) {
  const text = page.getByText(UNSAVED);
  if (visible) {
    await text.waitFor({ state: "visible", timeout: 8000 });
  } else {
    await page.waitForTimeout(300);
    assert((await text.count()) === 0, "Unexpected unsaved confirm");
  }
}

async function clickConfirm(page, label) {
  await page.getByRole("button", { name: label, exact: true }).click({ force: true });
}

async function clickSidebar(page, nameRe) {
  const source = nameRe.source;
  const ok = await page.evaluate((src) => {
    const re = new RegExp(src, "i");
    const link = Array.from(document.querySelectorAll("a.sidebar-link")).find((a) =>
      re.test(a.textContent || ""),
    );
    if (!link) return false;
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    return true;
  }, source);
  assert(ok, `Sidebar link not found: ${source}`);
}

async function apiJson(token, method, urlPath, body, isForm = false) {
  const headers = {
    Authorization: `Bearer ${token}`,
    "X-Organization-Id": process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010",
  };
  let bodyInit;
  if (isForm) {
    bodyInit = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    bodyInit = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${urlPath}`, { method, headers, body: bodyInit });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }
  return { status: res.status, json };
}

async function runScraperWizard(page, results) {
  await page.goto(`${BASE}/operations/new/scraper`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  const select = page.locator("#scraper-wizard-adapter");
  await select.waitFor({ timeout: 20000 });
  const optionCount = await select.locator("option").count();
  assert(optionCount >= 2, `Scraper wizard needs adapters, got ${optionCount} options`);

  // clean leave
  await page.getByRole("button", { name: /İptal|Vazgeç/i }).first().click();
  await expectUnsaved(page, false);
  results.push("scraper clean leave: PASS");

  await page.goto(`${BASE}/operations/new/scraper`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  await select.waitFor({ timeout: 20000 });
  await select.selectOption({ index: 1 });
  const dirtyValue = await select.inputValue();
  assert(Boolean(dirtyValue), "adapter selection empty");
  await page.waitForTimeout(250);

  // sidebar leave → confirm
  await clickSidebar(page, /Otomasyonlar|Dashboard/i);
  await expectUnsaved(page, true);
  await clickConfirm(page, "Forma Dön");
  assert(page.url().includes("/operations/new/scraper"), "Forma Dön should keep wizard");
  assert((await select.inputValue()) === dirtyValue, "adapter selection preserved");
  results.push("scraper dirty Forma Dön: PASS");

  // revert → clean
  await select.selectOption({ index: 0 });
  await page.waitForTimeout(250);
  await page.getByRole("button", { name: /İptal|Vazgeç/i }).first().click();
  await expectUnsaved(page, false);
  results.push("scraper revert clean: PASS");

  // dirty again + browser back Çık via SPA history (modal type picker → scraper)
  await clickSidebar(page, /Otomasyonlar/i);
  await page.waitForTimeout(700);
  await page.getByRole("button", { name: /Yeni Otomasyon/i }).first().click();
  await page.waitForSelector("#new-operation-type", { timeout: 15000 });
  await page.locator("#new-operation-type").selectOption("scraper");
  await page.getByRole("button", { name: /Devam Et/i }).click();
  await page.waitForURL(/\/operations\/new\/scraper/, { timeout: 15000 });
  await page.waitForTimeout(1000);
  await page.locator("#scraper-wizard-adapter").waitFor({ timeout: 20000 });
  await page.locator("#scraper-wizard-adapter").selectOption({ index: 1 });
  await page.waitForTimeout(300);
  await page.goBack();
  await expectUnsaved(page, true);
  await clickConfirm(page, "Çık");
  await page.waitForTimeout(400);
  assert(!page.url().includes("/operations/new/scraper"), "Çık should leave wizard");
  results.push("scraper dirty browser back Çık: PASS");
  results.push("Scraper Wizard dirty → PASS");
}

async function runSaveSuccess(page, token, results) {
  const unique = `DirtySave ${Date.now()}`;

  await page.goto(`${BASE}/customers`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: /Yeni Müşteri/i }).click();
  await page.waitForSelector("#customer-display-name");
  await page.locator("#customer-display-name").fill(unique);
  await page.waitForTimeout(200);

  // prove dirty before save
  await page.locator('[role="dialog"] .modal-header button').first().click();
  await expectUnsaved(page, true);
  await clickConfirm(page, "Forma Dön");
  assert((await page.locator("#customer-display-name").inputValue()) === unique, "name kept");

  const createRespPromise = page.waitForResponse(
    (res) =>
      res.request().method() === "POST" &&
      /\/api\/v1\/customers\/?$/.test(new URL(res.url()).pathname) &&
      (res.status() === 200 || res.status() === 201),
    { timeout: 45000 },
  );
  await page.locator('[role="dialog"] button[type="submit"]').click();
  const createResp = await createRespPromise;
  assert(
    createResp.status() === 200 || createResp.status() === 201,
    `Create API failed status=${createResp.status()}`,
  );
  await page.waitForTimeout(500);
  assert((await page.locator('[role="dialog"]').count()) === 0, "Modal should close after save");

  // Re-open create and leave clean — dirty must be reset (new form baseline)
  await page.getByRole("button", { name: /Yeni Müşteri/i }).click();
  await page.waitForSelector("#customer-display-name");
  await page.locator('[role="dialog"] .modal-header button').first().click();
  await expectUnsaved(page, false);

  const list = await apiJson(
    token,
    "GET",
    `/api/v1/customers?search=${encodeURIComponent(unique)}&page=1&pageSize=5`,
  );
  assert(list.status === 200, `customer search failed ${list.status}`);
  const items = list.json?.items || list.json?.data || [];
  const created = items.find((c) => c.display_name === unique) || items[0];
  assert(created?.id, "created customer not found via API");

  await page.goto(`${BASE}/customers/${created.id}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  const editBtn = page.getByRole("button", { name: /Düzenle/i }).first();
  await editBtn.click();
  await page.waitForSelector("#customer-display-name");
  const original = await page.locator("#customer-display-name").inputValue();
  const edited = `${original} X`;
  await page.locator("#customer-display-name").fill(edited);
  await page.waitForTimeout(200);

  const updateRespPromise = page.waitForResponse(
    (res) =>
      (res.request().method() === "PUT" || res.request().method() === "PATCH") &&
      res.url().includes(`/api/v1/customers/${created.id}`) &&
      (res.status() === 200 || res.status() === 204),
    { timeout: 45000 },
  );
  await page.locator('[role="dialog"] button[type="submit"]').click();
  const updateResp = await updateRespPromise;
  assert(
    updateResp.status() === 200 || updateResp.status() === 204,
    `Update API failed status=${updateResp.status()}`,
  );
  await page.waitForTimeout(500);
  assert((await page.locator('[role="dialog"]').count()) === 0, "Edit modal closed after save");

  await editBtn.click();
  await page.waitForSelector("#customer-display-name");
  await page.locator('[role="dialog"] .modal-header button').first().click();
  await expectUnsaved(page, false);

  results.push("Save-success dirty reset → PASS");
}

async function runImportSheetHeader(page, token, results) {
  assert(fs.existsSync(XLSX), `sample xlsx missing: ${XLSX}`);

  const fairs = await apiJson(token, "GET", "/api/v1/fairs?page=1&pageSize=20");
  assert(fairs.status === 200, `fairs list failed ${fairs.status}`);
  const fair = (fairs.json?.items || [])[0];
  assert(fair?.id, "No fair available for import upload");

  const form = new FormData();
  const buf = fs.readFileSync(XLSX);
  form.append(
    "file",
    new Blob([buf], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }),
    "dirty_accept.xlsx",
  );
  form.append("fair_id", fair.id);

  const upload = await apiJson(token, "POST", "/api/v1/data-integration/imports/upload", form, true);
  assert(
    upload.status === 200 || upload.status === 201,
    `upload failed status=${upload.status} body=${JSON.stringify(upload.json)?.slice(0, 300)}`,
  );
  const batchId = upload.json?.batch_id;
  assert(batchId, `upload missing batch_id: ${JSON.stringify(upload.json)?.slice(0, 300)}`);

  await page.goto(`${BASE}/data-integration/imports/continue/${batchId}`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForSelector("#import-sheet-select, #import-header-no-header", {
    timeout: 30000,
  });
  await page.waitForTimeout(500);

  const sheetSelect = page.locator("#import-sheet-select");
  const headerNo = page.locator("#import-header-no-header");

  if ((await sheetSelect.count()) > 0) {
    await sheetSelect.waitFor({ state: "visible", timeout: 10000 });
    const options = await sheetSelect.locator("option").allTextContents();
    assert(options.length >= 2, `Need ≥2 sheets for dirty test, got ${options.join(",")}`);
    const initial = await sheetSelect.inputValue();
    const other = options.find((o) => o && o !== initial) || options[1];
    await sheetSelect.selectOption({ label: other });
    await page.waitForTimeout(300);

    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, true);
    await clickConfirm(page, "Forma Dön");
    assert((await sheetSelect.inputValue()) === other, `sheet not preserved got=${await sheetSelect.inputValue()}`);

    await sheetSelect.selectOption({ label: initial });
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, false);
    results.push("import sheet revert clean: PASS");

    // dirty again and discard via sidebar
    await page.goto(`${BASE}/data-integration/imports/continue/${batchId}`, {
      waitUntil: "domcontentloaded",
    });
    await page.waitForSelector("#import-sheet-select", { timeout: 20000 });
    await page.locator("#import-sheet-select").selectOption({ label: other });
    await page.waitForTimeout(300);
    await clickSidebar(page, /Dashboard|Müşteriler/i);
    await expectUnsaved(page, true);
    await clickConfirm(page, "Çık");
    results.push("import sheet unsaved guard: PASS");

    // Header unsaved guard on same batch after confirming sheet via API-less UI Next
    await page.goto(`${BASE}/data-integration/imports/continue/${batchId}`, {
      waitUntil: "domcontentloaded",
    });
    await page.waitForSelector("#import-sheet-select", { timeout: 20000 });
    // Confirm sheet to advance to header (persists sheet → dirty clears for sheet)
    await page.getByRole("button", { name: /İleri|Sonraki|Devam/i }).first().click();
    await page.waitForSelector("#import-header-no-header, #import-header-first-row", {
      timeout: 30000,
    });
    const first = page.locator("#import-header-first-row");
    const wasFirst = await first.isChecked();
    if (wasFirst) await headerNo.click();
    else await first.click();
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, true);
    await clickConfirm(page, "Forma Dön");
    if (wasFirst) await first.click();
    else await headerNo.click();
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, false);
    results.push("import header unsaved guard: PASS");
  } else if ((await headerNo.count()) > 0) {
    const first = page.locator("#import-header-first-row");
    const wasFirst = await first.isChecked();
    if (wasFirst) await headerNo.click();
    else await first.click();
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, true);
    await clickConfirm(page, "Forma Dön");
    if (wasFirst) await first.click();
    else await headerNo.click();
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /İptal/i }).first().click();
    await expectUnsaved(page, false);
    results.push("import header unsaved guard: PASS");
  } else {
    throw new Error("Resume batch did not land on sheet or header step");
  }

  results.push("Import sheet/header unsaved guard → PASS");
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];
  try {
    const token = await login(page);
    await runScraperWizard(page, results);
    await runSaveSuccess(page, token, results);
    await runImportSheetHeader(page, token, results);
    console.log("REMAINING DIRTY ACCEPTANCE RESULTS");
    for (const line of results) console.log(`- ${line}`);
    const failed = results.some((l) => l.includes("FAIL"));
    if (failed) process.exitCode = 1;
  } catch (err) {
    console.error("ACCEPTANCE FAILED:", err);
    console.log("PARTIAL");
    for (const line of results) console.log(`- ${line}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await main();
