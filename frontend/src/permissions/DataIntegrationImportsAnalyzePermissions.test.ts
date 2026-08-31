import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/DataIntegrationImportsPage.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./importPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Data Integration imports analyze permission", () => {
  it("uses canonical imports update permission", () => {
    expect(permissionSource).toContain('IMPORT_PERMISSION_UPDATE = "fair_crm.imports.update"');
    expect(source).toContain("const canUpdate = can(IMPORT_PERMISSION_UPDATE)");
  });

  it("hides and fails closed analyze actions without update permission", () => {
    expect(source).toContain("if (!canUpdate) return;");
    expect(source).toContain("handlers.canUpdate && canAnalyze(batch.status)");
    expect(source).toContain("handlers.canUpdate && canReanalyze(batch.status)");
  });
});
