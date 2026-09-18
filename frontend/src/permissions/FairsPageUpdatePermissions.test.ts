import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/FairsPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");
const permissionSource = readFileSync(
  fileURLToPath(new URL("./fairPermissions.ts", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fairs page update permission", () => {
  it("uses canonical fairs update permission", () => {
    expect(permissionSource).toContain('FAIR_UPDATE = "fair_crm.fairs.update"');
    expect(source).toContain("const canUpdate = can(FAIR_UPDATE)");
  });

  it("fails closed for update handler", () => {
    expect(source).toContain("if (!canUpdate) return;");
    expect(source).toContain("canUpdate");
  });
});
