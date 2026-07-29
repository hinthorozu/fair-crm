/**
 * Fair Detail: move all participants source → target (real browser).
 *
 * Seed: Source X = A,B,C ; Target Y = C,D
 * Expect after move: X=0, Y=A,B,C,D (C once)
 */
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";

const BASE = process.env.FAIR_CRM_BASE_URL || "http://127.0.0.1:18173";
const API = process.env.FAIR_CRM_API_BASE || "http://127.0.0.1:18001";
const ORG_ID = process.env.VITE_ORGANIZATION_ID || "00000000-0000-4000-8000-000000000010";
const TOKEN = process.env.VITE_DEV_BYPASS_TOKEN || "dev-bypass";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "X-Organization-Id": ORG_ID,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  return { status: res.status, json, text };
}

function psql(sql) {
  return execFileSync(
    "docker",
    [
      "exec",
      "-e",
      "PGPASSWORD=postgres",
      "kyrox-postgres-dev",
      "psql",
      "-U",
      "postgres",
      "-d",
      "fair_crm",
      "-t",
      "-A",
      "-c",
      sql,
    ],
    { encoding: "utf8" },
  ).trim();
}

function countParticipationsIncludingDeleted(fairId) {
  return Number(
    psql(
      `SELECT COUNT(*) FROM crm_customer_fair_participations WHERE fair_id='${fairId}'`,
    ),
  );
}

function countActiveParticipations(fairId) {
  return Number(
    psql(
      `SELECT COUNT(*) FROM crm_customer_fair_participations WHERE organization_id='${ORG_ID}' AND fair_id='${fairId}' AND deleted_at IS NULL`,
    ),
  );
}

function fairExists(fairId) {
  return psql(`SELECT COUNT(*) FROM crm_fairs WHERE id='${fairId}'`) === "1";
}

function customersExist(ids) {
  const list = ids.map((id) => `'${id}'`).join(",");
  return Number(
    psql(
      `SELECT COUNT(*) FROM crm_customers WHERE organization_id='${ORG_ID}' AND id IN (${list}) AND deleted_at IS NULL`,
    ),
  );
}

async function seed(stamp) {
  const sourceName = `MOVE SRC X ${stamp}`;
  const targetName = `MOVE TGT Y ${stamp}`;
  const source = await api("POST", "/api/v1/fairs", { name: sourceName, status: "planned" });
  assert(source.status === 201, `source fair: ${source.text}`);
  const target = await api("POST", "/api/v1/fairs", { name: targetName, status: "planned" });
  assert(target.status === 201, `target fair: ${target.text}`);

  const mkCustomer = async (name) => {
    const res = await api("POST", "/api/v1/customers", { display_name: name, status: "active" });
    assert(res.status === 201, `customer ${name}: ${res.text}`);
    return res.json.id;
  };
  const a = await mkCustomer(`Move A ${stamp}`);
  const b = await mkCustomer(`Move B ${stamp}`);
  const c = await mkCustomer(`Move C ${stamp}`);
  const d = await mkCustomer(`Move D ${stamp}`);

  const link = async (customerId, fairId, hall) => {
    const res = await api("POST", "/api/v1/fair-participations", {
      customer_id: customerId,
      fair_id: fairId,
      hall,
    });
    assert(res.status === 201, `participation: ${res.text}`);
  };
  await link(a, source.json.id, "XA");
  await link(b, source.json.id, "XB");
  await link(c, source.json.id, "XC");
  await link(c, target.json.id, "YC");
  await link(d, target.json.id, "YD");

  return {
    sourceId: source.json.id,
    targetId: target.json.id,
    sourceName,
    targetName,
    customers: { a, b, c, d },
  };
}

async function main() {
  const stamp = Date.now().toString(36);
  const seeded = await seed(stamp);
  console.log("seeded", seeded);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript(
    ({ orgId, token }) => {
      localStorage.setItem(
        "fair-crm.auth.session",
        JSON.stringify({
          accessToken: token,
          organizationId: orgId,
          user: { id: "00000000-0000-4000-8000-000000000099", email: "e2e@local" },
        }),
      );
    },
    { orgId: ORG_ID, token: TOKEN },
  );

  const moveResponsePromise = page.waitForResponse(
    (res) =>
      res.url().includes(`/api/v1/fairs/${seeded.sourceId}/participants/move-to-fair`) &&
      res.request().method() === "POST",
    { timeout: 30000 },
  );

  await page.goto(`${BASE}/fairs/${seeded.sourceId}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Müşterileri Başka Fuara Taşı" }).click();
  const fairInput = page.locator("#move-customers-target-fair");
  await fairInput.waitFor({ timeout: 15000 });
  await fairInput.click();
  await fairInput.fill(seeded.targetName);
  await page.waitForSelector(".entity-select-dropdown", { timeout: 8000 });
  await page.waitForTimeout(500);
  await page
    .locator(".entity-select-option-label")
    .filter({ hasText: seeded.targetName })
    .first()
    .click();
  await page
    .locator('[data-testid="move-customers-confirm-text"]')
    .filter({ hasText: seeded.targetName })
    .waitFor({ timeout: 10000 });

  const confirmText = await page.locator('[data-testid="move-customers-confirm-text"]').innerText();
  assert(
    confirmText.includes(seeded.targetName),
    `confirmation missing target name: ${confirmText}`,
  );

  await page.getByRole("button", { name: "Taşı", exact: true }).click();
  const moveRes = await moveResponsePromise;
  const moveBody = await moveRes.json();
  assert(moveRes.status() === 200, `move http ${moveRes.status()} ${JSON.stringify(moveBody)}`);
  assert(moveBody.source_remaining === 0, `source_remaining ${moveBody.source_remaining}`);
  assert(moveBody.moved_count === 2, `moved_count ${moveBody.moved_count}`);
  assert(moveBody.already_on_target_count === 1, `dupes ${moveBody.already_on_target_count}`);

  await page.getByText("Müşteriler hedef fuara taşındı.").waitFor({ timeout: 10000 });

  // Badge / count should refresh without full reload
  await page.waitForTimeout(800);
  const sourceList = await api("GET", `/api/v1/fairs/${seeded.sourceId}/participants?pageSize=50`);
  const targetList = await api("GET", `/api/v1/fairs/${seeded.targetId}/participants?pageSize=50`);
  assert(sourceList.status === 200, sourceList.text);
  assert(targetList.status === 200, targetList.text);
  assert(sourceList.json.pagination.totalItems === 0, `source count ${sourceList.json.pagination.totalItems}`);
  assert(targetList.json.pagination.totalItems === 4, `target count ${targetList.json.pagination.totalItems}`);
  const names = new Set(targetList.json.items.map((i) => i.company_name));
  assert(names.size === 4, `unique names ${[...names]}`);
  const cRows = targetList.json.items.filter((i) => i.customer_id === seeded.customers.c);
  assert(cRows.length === 1, `C duplicate rows ${cRows.length}`);
  assert(cRows[0].hall === "YC", `C hall preserved on target: ${cRows[0].hall}`);

  const dbSource = countParticipationsIncludingDeleted(seeded.sourceId);
  const dbTarget = countActiveParticipations(seeded.targetId);
  assert(dbSource === 0, `db source including soft-deleted ${dbSource}`);
  assert(dbTarget === 4, `db target ${dbTarget}`);
  assert(fairExists(seeded.sourceId), "source fair deleted");
  assert(customersExist(Object.values(seeded.customers)) === 4, "customers missing");

  await browser.close();
  console.log(
    JSON.stringify({
      ok: true,
      sourceId: seeded.sourceId,
      targetId: seeded.targetId,
      sourceCount: 0,
      targetCount: 4,
      moveBody,
    }),
  );
  console.log("UI_TEST PASS");
}

main().catch((err) => {
  console.error("UI_TEST FAIL", err);
  process.exit(1);
});
