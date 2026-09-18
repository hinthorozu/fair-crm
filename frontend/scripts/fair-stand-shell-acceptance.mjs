/**
 * Login → Fair CRM shell → Fair Stand menu → configurator visible.
 *
 * Usage (from frontend/, with CRM + Core available):
 *   node scripts/fair-stand-shell-acceptance.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const EMAIL = process.env.FAIR_CRM_DEV_EMAIL || "dev@example.com";
const PASSWORD = process.env.FAIR_CRM_DEV_PASSWORD || "DevPassword123!";

async function countFairStandRuntime(page) {
  const frames = page.locator('[data-testid="fair-stand-frame"]');
  const frameCount = await frames.count();
  const canvasCount = await page
    .frameLocator('[data-testid="fair-stand-frame"]')
    .locator("canvas")
    .count()
    .catch(() => 0);
  const hostCanvasCount = await page.locator('[data-testid="fair-stand-host"] canvas').count();
  return { frameCount, canvasCount, hostCanvasCount };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    const location = msg.location();
    consoleErrors.push(`${text}${location?.url ? ` @ ${location.url}` : ""}`);
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });

  try {
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    if (page.url().includes("/login")) {
      await page.fill("#login-email", EMAIL);
      await page.fill("#login-password", PASSWORD);
      await Promise.all([
        page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30_000 }),
        page.click("button[type='submit']"),
      ]);
    }

    const fairStandNav = page.getByRole("link", { name: "Fair Stand" });
    await fairStandNav.waitFor({ state: "visible", timeout: 15_000 });
    await fairStandNav.click();
    await page.waitForURL((url) => url.pathname === "/fair-stand", { timeout: 15_000 });

    const sidebar = page.locator("aside.sidebar").first();
    if (!(await sidebar.isVisible())) {
      throw new Error("CRM sidebar missing on /fair-stand");
    }

    const frame = page.frameLocator('[data-testid="fair-stand-frame"]');
    await frame.getByRole("heading", { name: "Maxima Stand Konfigüratörü" }).waitFor({
      state: "visible",
      timeout: 30_000,
    });
    await frame.locator("#viewport-empty").waitFor({ state: "visible", timeout: 15_000 });

    await page.getByRole("link", { name: "Dashboard" }).click();
    await page.waitForURL((url) => url.pathname === "/dashboard", { timeout: 15_000 });
    const dashboardRuntime = await countFairStandRuntime(page);
    if (dashboardRuntime.frameCount !== 0) {
      throw new Error(`Fair Stand iframe leaked onto Dashboard: ${dashboardRuntime.frameCount}`);
    }

    await page.getByRole("link", { name: "Fair Stand" }).click();
    await page.waitForURL((url) => url.pathname === "/fair-stand", { timeout: 15_000 });
    await frame.getByRole("heading", { name: "Maxima Stand Konfigüratörü" }).waitFor({
      state: "visible",
      timeout: 15_000,
    });
    await frame.locator("#viewport-empty").waitFor({ state: "visible", timeout: 15_000 });

    const remountRuntime = await countFairStandRuntime(page);
    if (remountRuntime.frameCount !== 1) {
      throw new Error(`Expected one Fair Stand iframe after remount, got ${remountRuntime.frameCount}`);
    }
    if (remountRuntime.hostCanvasCount !== 0) {
      throw new Error(`Canvas leaked into CRM host: ${remountRuntime.hostCanvasCount}`);
    }

    const iframeSrc = await page.locator('[data-testid="fair-stand-frame"]').getAttribute("src");
    if (iframeSrc && /5174|fair-stand/i.test(iframeSrc)) {
      throw new Error(`Fair Stand iframe loaded a separate origin: ${iframeSrc}`);
    }

    if (pageErrors.length) {
      throw new Error(`pageerror: ${pageErrors.join(" | ")}`);
    }
    if (consoleErrors.length) {
      throw new Error(`console error: ${consoleErrors.join(" | ")}`);
    }

    console.log(
      `fair_stand_shell_ok iframe_src=${iframeSrc ?? "<none>"} frames=${remountRuntime.frameCount} iframe_canvas=${remountRuntime.canvasCount}`,
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
