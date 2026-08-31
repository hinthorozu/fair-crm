import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/FairsPage.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./fairPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Fairs page create permission", () => {
  it("uses canonical fairs create permission", () => {
    expect(permissionSource).toContain('FAIR_CREATE = "fair_crm.fairs.create"');
    expect(source).toContain("const canCreate = can(FAIR_CREATE)");
  });

  it("fails closed for create handlers", () => {
    expect(source.match(/if \(!canCreate\) return;/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
    expect(source).toContain("onCreate={canCreate ? openCreate : undefined}");
  });
});
