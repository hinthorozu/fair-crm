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
  const frameCount = await page.locator('[data-testid="fair-stand-frame"]').count();
  const hostCanvasCount = await page.locator('[data-testid="fair-stand-host"] canvas').count();
  const mountStyleCount = await page.locator("style[data-fair-stand-mount]").count();
  return { frameCount, hostCanvasCount, mountStyleCount };
}

function assertSameOrigin(page) {
  const origin = new URL(page.url()).origin;
  if (origin !== new URL(BASE).origin) {
    throw new Error(`Fair Stand left the CRM origin: ${page.url()}`);
  }
  if (/5174/.test(page.url())) {
    throw new Error(`Fair Stand loaded a separate dev server: ${page.url()}`);
  }
}

async function assertNoStandLeak(page, where) {
  const runtime = await countFairStandRuntime(page);
  if (runtime.frameCount !== 0) {
    throw new Error(`Fair Stand iframe leaked onto ${where}: ${runtime.frameCount}`);
  }
  if (runtime.hostCanvasCount !== 0) {
    throw new Error(`Fair Stand canvas leaked onto ${where}: ${runtime.hostCanvasCount}`);
  }
  if (runtime.mountStyleCount !== 0) {
    throw new Error(`Fair Stand mount style leaked onto ${where}: ${runtime.mountStyleCount}`);
  }
}

async function assertSameDocumentFairStand(page) {
  assertSameOrigin(page);
  if (await page.locator(".app-shell").count()) {
    throw new Error("CRM shell is present on the stand editor");
  }
  if (await page.locator("nav.sidebar-nav").count()) {
    throw new Error("CRM sidebar is present on the stand editor");
  }
  if (await page.locator("header.app-topbar").count()) {
    throw new Error("CRM topbar is present on the stand editor");
  }
  if (await page.locator(".breadcrumb").count()) {
    throw new Error("CRM breadcrumb is present on the stand editor");
  }
  await page.getByTestId("fair-stand-standalone").waitFor({ state: "visible", timeout: 15_000 });
  await page.getByTestId("fair-stand-host").waitFor({ state: "visible", timeout: 15_000 });
  await page.getByRole("heading", { name: "Maxima Konfigüratörü" }).waitFor({
    state: "visible",
    timeout: 30_000,
  });
  await page.locator("#viewport-empty").waitFor({ state: "attached", timeout: 15_000 });
  await page.locator('[data-testid="fair-stand-host"] canvas').first().waitFor({
    state: "attached",
    timeout: 30_000,
  });
  await page.locator(".sidebar-back").waitFor({ state: "visible", timeout: 15_000 });

  const runtime = await countFairStandRuntime(page);
  if (runtime.frameCount !== 0) {
    throw new Error(`Expected no Fair Stand iframe, got ${runtime.frameCount}`);
  }
  if (runtime.hostCanvasCount < 1) {
    throw new Error("Fair Stand canvas is missing from the host document");
  }
  if (runtime.mountStyleCount !== 1) {
    throw new Error(`Expected one Fair Stand mount style, got ${runtime.mountStyleCount}`);
  }

  const box = await page.getByTestId("fair-stand-standalone").boundingBox();
  const viewport = page.viewportSize();
  if (!box || !viewport) throw new Error("Could not measure Fair Stand viewport");
  if (box.width < viewport.width - 2 || box.height < viewport.height - 2) {
    throw new Error(
      `Fair Stand does not fill the viewport: host=${box.width}x${box.height} viewport=${viewport.width}x${viewport.height}`,
    );
  }
  return { box, runtime };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (msg) => recordConsoleError(consoleErrors, msg));
  page.on("response", (response) => recordFailedResponse(consoleErrors, response));
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

    const fairStandNav = page.getByRole("link", { name: "Standlar" });
    await fairStandNav.waitFor({ state: "visible", timeout: 15_000 });
    await expectNavOpensNewTab(fairStandNav);

    const crmPath = new URL(page.url()).pathname;
    const [projectList] = await Promise.all([
      page.waitForEvent("popup"),
      fairStandNav.click(),
    ]);
    const watchPage = (target) => {
      target.on("console", (msg) => recordConsoleError(consoleErrors, msg));
      target.on("pageerror", (error) => {
        pageErrors.push(error.message);
      });
      target.on("response", (response) => recordFailedResponse(consoleErrors, response));
    };
    watchPage(projectList);
    await projectList.waitForURL((url) => url.pathname === "/stand-projects", { timeout: 15_000 });
    if (new URL(page.url()).pathname !== crmPath) {
      throw new Error(`CRM tab navigated away from ${crmPath} to ${page.url()}`);
    }
    if (await page.locator("aside.sidebar").count() === 0) {
      throw new Error("CRM sidebar missing on the original CRM tab");
    }

    const editButton = projectList.getByRole("button", { name: "Düzenle" }).first();
    await editButton.waitFor({ state: "visible", timeout: 15_000 });
    const [editor] = await Promise.all([
      projectList.waitForEvent("popup"),
      editButton.click(),
    ]);
    watchPage(editor);
    await editor.waitForURL((url) => /^\/stand-projects\/[^/]+$/.test(url.pathname), { timeout: 15_000 });
    const editorState = await assertSameDocumentFairStand(editor);

    await editor.locator(".sidebar-back").click();
    await editor.waitForURL((url) => url.pathname === "/stand-projects", { timeout: 15_000 });
    await assertNoStandLeak(editor, "stand project list");

    await page.getByRole("link", { name: "Dashboard" }).click();
    await page.waitForURL((url) => url.pathname === "/dashboard", { timeout: 15_000 });
    await assertNoStandLeak(page, "Dashboard");

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
      `fair_stand_same_document_ok frames=${editorState.runtime.frameCount} host_canvas=${editorState.runtime.hostCanvasCount} styles=${editorState.runtime.mountStyleCount} size=${Math.round(editorState.box.width)}x${Math.round(editorState.box.height)}`,
    );
  } finally {
    await browser.close();
  }
}

function recordConsoleError(consoleErrors, msg) {
  if (msg.type() !== "error") return;
  const text = msg.text();
  if (text.startsWith("Failed to load resource:")) return;
  const location = msg.location();
  consoleErrors.push(`${text}${location?.url ? ` @ ${location.url}` : ""}`);
}

function recordFailedResponse(consoleErrors, response) {
  if (response.status() < 400) return;
  const url = new URL(response.url());
  if (/^\/api\/v1\/customers\/[^/]+$/.test(url.pathname)) return;
  consoleErrors.push(`${response.status()} ${response.url()}`);
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
