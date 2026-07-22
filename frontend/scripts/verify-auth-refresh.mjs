/**
 * Live browser verification: login → wait for access expiry → silent refresh → logout.
 * Does not print token values.
 *
 * Usage (from frontend/):
 *   node scripts/verify-auth-refresh.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const EMAIL = process.env.FAIR_CRM_DEV_EMAIL || "dev@example.com";
const PASSWORD = process.env.FAIR_CRM_DEV_PASSWORD || "DevPassword123!";
const WAIT_MS = Number(process.env.AUTH_REFRESH_WAIT_MS || 70_000);

function jwtTtlSeconds(token) {
  const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
  return payload.exp - payload.iat;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const refreshUrls = [];
  const api401s = [];
  const consoleErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("/api/v1/auth/refresh")) {
      refreshUrls.push({ status: response.status(), url });
    }
    if (url.includes("/api/v1/") && !url.includes("/api/v1/auth/") && response.status() === 401) {
      api401s.push(url);
    }
  });

  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30_000 }),
    page.click('button[type="submit"]'),
  ]);

  const session1 = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  if (!session1?.accessToken) {
    throw new Error("LOGIN_FAIL: no access token in localStorage");
  }
  if (session1.refreshToken) {
    throw new Error("SECURITY_FAIL: refresh token present in localStorage");
  }
  const ttl = jwtTtlSeconds(session1.accessToken);
  console.log(`login_ok ttl_seconds=${ttl} path=${page.url()}`);

  const cookies = await context.cookies();
  const refreshCookie = cookies.find((c) => c.name === "fair_crm_refresh_token");
  if (!refreshCookie) {
    throw new Error("COOKIE_FAIL: fair_crm_refresh_token missing after login");
  }
  if (!refreshCookie.httpOnly) {
    throw new Error("COOKIE_FAIL: refresh cookie not HttpOnly");
  }
  console.log(
    `cookie_ok httpOnly=${refreshCookie.httpOnly} sameSite=${refreshCookie.sameSite} path=${refreshCookie.path}`,
  );

  console.log(`waiting_ms=${WAIT_MS} for access token expiry...`);
  await page.waitForTimeout(WAIT_MS);

  // Trigger authenticated API traffic after expiry.
  await page.goto(`${BASE}/customers`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2_000);

  const session2 = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  if (!session2?.accessToken) {
    throw new Error("REFRESH_FAIL: session cleared after expiry");
  }
  if (session2.accessToken === session1.accessToken) {
    throw new Error("REFRESH_FAIL: access token unchanged after expiry window");
  }
  if (!refreshUrls.some((r) => r.status === 200)) {
    throw new Error(`REFRESH_FAIL: no successful /auth/refresh (seen=${JSON.stringify(refreshUrls)})`);
  }
  if (page.url().includes("/login")) {
    throw new Error("REFRESH_FAIL: redirected to login after expiry");
  }
  console.log(
    `refresh_ok refresh_calls=${refreshUrls.length} still_on_app=${!page.url().includes("/login")}`,
  );

  // Logout
  const logoutBtn = page.getByRole("button", { name: /çıkış|logout/i });
  if (await logoutBtn.count()) {
    await logoutBtn.first().click();
    await page.waitForTimeout(1_000);
  } else {
    await page.evaluate(async () => {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-Fair-CRM-Requested-With": "XMLHttpRequest",
        },
        body: "{}",
      });
      localStorage.removeItem("fair-crm.auth.session");
    });
  }

  const refreshAfterLogout = await page.evaluate(async () => {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Fair-CRM-Requested-With": "XMLHttpRequest",
      },
      body: "{}",
    });
    return res.status;
  });
  if (refreshAfterLogout === 200) {
    throw new Error("LOGOUT_FAIL: refresh still works after logout");
  }
  console.log(`logout_ok refresh_status=${refreshAfterLogout}`);

  const filteredConsole = consoleErrors.filter(
    (t) =>
      !/favicon|Download the React DevTools/i.test(t) &&
      // Browser logs a console error for the initial 401 before silent refresh retries.
      !/Failed to load resource: the server responded with a status of 401/i.test(t),
  );
  if (filteredConsole.length) {
    console.log(`console_errors=${filteredConsole.length}`);
    for (const err of filteredConsole.slice(0, 5)) console.log(`console_error=${err}`);
    throw new Error("CONSOLE_FAIL");
  }

  console.log("VERIFY_PASS");
  await browser.close();
}

main().catch(async (err) => {
  console.error("VERIFY_FAIL", err.message || err);
  process.exit(1);
});
