/**
 * Live browser verification for 15-day auth session.
 * Does not print token values.
 *
 * Usage (from frontend/):
 *   node scripts/verify-auth-refresh.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:5173";
const EMAIL = process.env.FAIR_CRM_DEV_EMAIL || "dev@example.com";
const PASSWORD = process.env.FAIR_CRM_DEV_PASSWORD || "DevPassword123!";
const FIFTEEN_DAYS_SECONDS = 15 * 24 * 60 * 60;
const SHORT_WAIT_MS = Number(process.env.AUTH_SESSION_SHORT_WAIT_MS || 20_000);

function jwtTtlSeconds(token) {
  const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
  return payload.exp - payload.iat;
}

function jwtExpIso(token) {
  const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
  return new Date(payload.exp * 1000).toISOString();
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const refreshUrls = [];
  const consoleErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/auth/refresh")) {
      refreshUrls.push({ status: response.status(), url });
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
  if (Math.abs(ttl - FIFTEEN_DAYS_SECONDS) > 5) {
    throw new Error(`TTL_FAIL: expected ~${FIFTEEN_DAYS_SECONDS}s got ${ttl}s`);
  }
  console.log(`login_ok ttl_seconds=${ttl} exp_iso=${jwtExpIso(session1.accessToken)} path=${page.url()}`);

  const cookies = await context.cookies();
  const refreshCookie = cookies.find((c) => c.name === "fair_crm_refresh_token");
  if (!refreshCookie) {
    throw new Error("COOKIE_FAIL: fair_crm_refresh_token missing after login");
  }
  if (!refreshCookie.httpOnly) {
    throw new Error("COOKIE_FAIL: refresh cookie not HttpOnly");
  }
  // Playwright exposes expires as unix seconds; Max-Age 15d ≈ now+15d.
  const cookieTtl = Math.round(refreshCookie.expires - Date.now() / 1000);
  if (Math.abs(cookieTtl - FIFTEEN_DAYS_SECONDS) > 120) {
    throw new Error(`COOKIE_MAX_AGE_FAIL: expected ~${FIFTEEN_DAYS_SECONDS}s got ${cookieTtl}s`);
  }
  console.log(
    `cookie_ok httpOnly=${refreshCookie.httpOnly} sameSite=${refreshCookie.sameSite} path=${refreshCookie.path} ttl_seconds=${cookieTtl}`,
  );

  // Prove short windows do not kick the user out (access JWT is 15 days).
  console.log(`short_wait_ms=${SHORT_WAIT_MS} (stand-in for >15min smoke under 15-day JWT)...`);
  await page.waitForTimeout(SHORT_WAIT_MS);
  await page.goto(`${BASE}/customers`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1_500);
  if (page.url().includes("/login")) {
    throw new Error("SESSION_FAIL: redirected to login after short wait");
  }
  const sessionAfterWait = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  if (!sessionAfterWait?.accessToken) {
    throw new Error("SESSION_FAIL: access token missing after short wait");
  }
  console.log("short_wait_ok still_authenticated=true");

  // Page reload keeps session (access in localStorage + refresh cookie).
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1_000);
  if (page.url().includes("/login")) {
    throw new Error("RELOAD_FAIL: redirected to login after reload");
  }
  const sessionAfterReload = await page.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  if (!sessionAfterReload?.accessToken) {
    throw new Error("RELOAD_FAIL: session missing after reload");
  }
  console.log("reload_ok still_authenticated=true");

  // Simulate browser reopen: new context with same storage/cookies.
  const storage = await context.storageState();
  await browser.close();

  const browser2 = await chromium.launch({ headless: true });
  const context2 = await browser2.newContext({ storageState: storage });
  const page2 = await context2.newPage();
  await page2.goto(`${BASE}/dashboard`, { waitUntil: "networkidle" });
  await page2.waitForTimeout(1_500);
  if (page2.url().includes("/login")) {
    throw new Error("REOPEN_FAIL: redirected to login after browser reopen");
  }
  const sessionReopen = await page2.evaluate(() => {
    const raw = localStorage.getItem("fair-crm.auth.session");
    return raw ? JSON.parse(raw) : null;
  });
  if (!sessionReopen?.accessToken) {
    throw new Error("REOPEN_FAIL: session missing after browser reopen");
  }
  console.log("reopen_ok still_authenticated=true");

  // Logout then refresh must fail.
  await page2.evaluate(async () => {
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
  const refreshAfterLogout = await page2.evaluate(async () => {
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
      !/Failed to load resource: the server responded with a status of 401/i.test(t),
  );
  if (filteredConsole.length) {
    console.log(`console_errors=${filteredConsole.length}`);
    for (const err of filteredConsole.slice(0, 5)) console.log(`console_error=${err}`);
    throw new Error("CONSOLE_FAIL");
  }

  console.log("VERIFY_PASS");
  await browser2.close();
}

main().catch((err) => {
  console.error("VERIFY_FAIL", err.message || err);
  process.exit(1);
});
