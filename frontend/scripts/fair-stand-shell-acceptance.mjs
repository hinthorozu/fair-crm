/**
 * Login → Fair CRM shell → Fair Stand menu opens a new tab → standalone configurator.
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

async function assertStandaloneFairStand(page) {
  if (await page.locator("aside.sidebar").count()) {
    throw new Error("CRM sidebar is present on standalone /fair-stand");
  }
  if (await page.locator("header.app-topbar").count()) {
    throw new Error("CRM topbar is present on standalone /fair-stand");
  }
  if (await page.locator(".breadcrumb").count()) {
    throw new Error("CRM breadcrumb is present on standalone /fair-stand");
  }
  await page.getByTestId("fair-stand-standalone").waitFor({ state: "visible", timeout: 15_000 });
  await page.getByTestId("fair-stand-host").waitFor({ state: "visible", timeout: 15_000 });

  const frame = page.frameLocator('[data-testid="fair-stand-frame"]');
  await frame.getByRole("heading", { name: "Maxima Stand Konfigüratörü" }).waitFor({
    state: "visible",
    timeout: 30_000,
  });
  await frame.locator("#viewport-empty").waitFor({ state: "visible", timeout: 15_000 });
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
    await expectNavOpensNewTab(fairStandNav);

    const crmPath = new URL(page.url()).pathname;
    const [standalone] = await Promise.all([
      page.waitForEvent("popup"),
      fairStandNav.click(),
    ]);
    standalone.on("console", (msg) => {
      if (msg.type() !== "error") return;
      consoleErrors.push(msg.text());
    });
    standalone.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });
    await standalone.waitForURL((url) => url.pathname === "/fair-stand", { timeout: 15_000 });
    if (new URL(page.url()).pathname !== crmPath) {
      throw new Error(`CRM tab navigated away from ${crmPath} to ${page.url()}`);
    }
    if (await page.locator("aside.sidebar").count() === 0) {
      throw new Error("CRM sidebar missing on the original CRM tab");
    }

    await assertStandaloneFairStand(standalone);

    const remountRuntime = await countFairStandRuntime(standalone);
    if (remountRuntime.frameCount !== 1) {
      throw new Error(`Expected one Fair Stand iframe after mount, got ${remountRuntime.frameCount}`);
    }
    if (remountRuntime.hostCanvasCount !== 0) {
      throw new Error(`Canvas leaked into CRM host: ${remountRuntime.hostCanvasCount}`);
    }

    const iframeSrc = await standalone.locator('[data-testid="fair-stand-frame"]').getAttribute("src");
    if (iframeSrc && /5174|fair-stand/i.test(iframeSrc)) {
      throw new Error(`Fair Stand iframe loaded a separate origin: ${iframeSrc}`);
    }

    const box = await standalone.getByTestId("fair-stand-standalone").boundingBox();
    const viewport = standalone.viewportSize();
    if (!box || !viewport) throw new Error("Could not measure Fair Stand viewport");
    if (box.width < viewport.width - 2 || box.height < viewport.height - 2) {
      throw new Error(
        `Fair Stand does not fill the viewport: host=${box.width}x${box.height} viewport=${viewport.width}x${viewport.height}`,
      );
    }

    await page.getByRole("link", { name: "Dashboard" }).click();
    await page.waitForURL((url) => url.pathname === "/dashboard", { timeout: 15_000 });
    const dashboardRuntime = await countFairStandRuntime(page);
    if (dashboardRuntime.frameCount !== 0) {
      throw new Error(`Fair Stand iframe leaked onto Dashboard: ${dashboardRuntime.frameCount}`);
    }

    const anonymous = await browser.newPage();
    await anonymous.goto(`${BASE}/fair-stand`, { waitUntil: "networkidle" });
    if (!anonymous.url().includes("/login")) {
      throw new Error(`Unauthenticated /fair-stand did not redirect to login: ${anonymous.url()}`);
    }
    await anonymous.close();

    if (pageErrors.length) {
      throw new Error(`pageerror: ${pageErrors.join(" | ")}`);
    }
    if (consoleErrors.length) {
      throw new Error(`console error: ${consoleErrors.join(" | ")}`);
    }

    console.log(
      `fair_stand_standalone_ok iframe_src=${iframeSrc ?? "<none>"} frames=${remountRuntime.frameCount} iframe_canvas=${remountRuntime.canvasCount} size=${Math.round(box.width)}x${Math.round(box.height)}`,
    );
  } finally {
    await browser.close();
  }
}

async function expectNavOpensNewTab(link) {
  const target = await link.getAttribute("target");
  const rel = await link.getAttribute("rel");
  if (target !== "_blank") throw new Error(`Fair Stand nav target is ${target}, expected _blank`);
  if (!rel?.includes("noopener") || !rel.includes("noreferrer")) {
    throw new Error(`Fair Stand nav rel is ${rel}, expected noopener noreferrer`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
