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

describe("Fairs page delete permission", () => {
  it("uses canonical fairs delete permission", () => {
    expect(permissionSource).toContain('FAIR_DELETE = "fair_crm.fairs.delete"');
    expect(source).toContain("const canDelete = can(FAIR_DELETE)");
  });

  it("fails closed for archive and restore handlers", () => {
    expect(source.match(/if \(!canDelete\) return;/g)?.length ?? 0).toBeGreaterThanOrEqual(2);
    expect(source).toContain("onArchive={canDelete");
    expect(source).toContain("onRestore={canDelete");
  });
});
