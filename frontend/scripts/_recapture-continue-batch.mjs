import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE = "http://127.0.0.1:5175";
const BATCH = "e302f4d8-5058-4753-afe6-186cf26e916f";
const ROUTE = "/data-integration/imports/continue/:batchId";
const URL_PATH = `/data-integration/imports/continue/${BATCH}`;
const WIDTHS = [320, 390, 767, 768, 769, 1023, 1024, 1025, 1439, 1440, 1441, 1920, 2560, 3440, 3840];
const OUT = path.resolve("reports/full-ui-evidence");
const SHOTS = path.join(OUT, "screenshots");

async function collectMetrics(page) {
  return page.evaluate(() => {
    const d = document.documentElement;
    const b = document.body;
    const overflowX = Math.max(0, Math.max(d.scrollWidth, b.scrollWidth) - d.clientWidth);
    const stretched = Array.from(document.querySelectorAll(".checkbox-field,.radio-field,.output-field-row")).filter(
      (el) => el.getBoundingClientRect().width > 480,
    ).length;
    const nativeChecks = Array.from(document.querySelectorAll('input[type="checkbox"],input[type="radio"]')).filter(
      (el) => {
        const s = getComputedStyle(el);
        return s.appearance !== "none" && s.webkitAppearance !== "none";
      },
    ).length;
    const href = location.href;
    const h1 = document.querySelector("h1")?.textContent?.trim() || null;
    const text = document.body?.innerText || "";
    const isWizard =
      !!document.querySelector(".import-wizard, [data-import-wizard], .wizard-steps, .wizard") ||
      /Kararlar|Excel Import|Sütun Eşleme|Önizleme|Birleştir/i.test(text) ||
      href.includes("/continue/");
    const redirected = !href.includes("/continue/");
    const batchMissing = /bulunamadı|not found|batch.*missing|yüklenemedi/i.test(text);
    return { overflowX, stretched, nativeChecks, href, h1, isWizard, redirected, batchMissing };
  });
}

async function main() {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ bypassCSP: true });
  const page = await context.newPage();
  const results = [];

  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: width >= 1440 ? 1080 : 900 });
    let status = "PASS";
    let reason = "";
    let metrics = {};
    try {
      await page.goto(`${BASE}${URL_PATH}`, { waitUntil: "networkidle", timeout: 45000 });
      await page.waitForTimeout(900);
      metrics = await collectMetrics(page);
      const bodyText = await page.evaluate(() => document.body?.innerText || "");
      const hrefOk = String(metrics.href || page.url()).includes("/continue/");
      const textOk = /Kararlar|Excel Import/i.test(bodyText);
      if (!hrefOk) {
        status = "FAIL";
        reason = "url-missing-continue";
      } else if (!textOk) {
        status = "FAIL";
        reason = "missing-Kararlar-or-Excel-Import";
      } else if (metrics.overflowX > 0) {
        status = "FAIL";
        reason = `overflowX=${metrics.overflowX}`;
      } else if (metrics.stretched > 0) {
        status = "FAIL";
        reason = `stretchedControls=${metrics.stretched}`;
      } else if (metrics.nativeChecks > 0) {
        status = "FAIL";
        reason = `nativeCheckboxRadio=${metrics.nativeChecks}`;
      }
    } catch (err) {
      status = "FAIL";
      reason = String(err.message || err).slice(0, 160);
    }

    const file = `data-integration_imports_continue_batchId__w${width}.png`;
    const shotPath = path.join(SHOTS, file);
    try {
      await page.screenshot({ path: shotPath, fullPage: false });
    } catch {
      status = "FAIL";
      reason = (reason ? reason + "; " : "") + "screenshot-failed";
    }

    const row = {
      route: ROUTE,
      url: URL_PATH,
      width,
      status,
      reason,
      kind: "di-param",
      production: true,
      screenshot: `screenshots/${file}`,
      metrics,
      captureKind: "metric",
    };
    results.push(row);
    console.log(`${status} w${width} ${reason} href=${metrics.href || ""} h1=${metrics.h1 || ""} overflowX=${metrics.overflowX ?? "?"} isWizard=${metrics.isWizard}`);
  }

  await browser.close();

  const capturePath = path.join(OUT, "capture-results.json");
  const capture = JSON.parse(fs.readFileSync(capturePath, "utf8"));
  capture.ids = { ...(capture.ids || {}), batchId: BATCH };
  capture.results = (capture.results || []).filter((r) => r.route !== ROUTE).concat(results);
  fs.writeFileSync(capturePath, JSON.stringify(capture, null, 2));
  fs.writeFileSync(path.join(OUT, "continue-batch-recapture.json"), JSON.stringify(results, null, 2));

  const pass = results.filter((r) => r.status === "PASS").length;
  const fail = results.filter((r) => r.status === "FAIL").length;
  console.log(`\nSUMMARY pass=${pass} fail=${fail} total=${results.length}`);
  console.log(`Updated ${capturePath}`);
  console.log(`Wrote ${path.join(OUT, "continue-batch-recapture.json")}`);
  console.log(`capture.ids.batchId=${capture.ids.batchId}`);
  console.log(`continue results in capture-results: ${capture.results.filter((r) => r.route === ROUTE).length}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
