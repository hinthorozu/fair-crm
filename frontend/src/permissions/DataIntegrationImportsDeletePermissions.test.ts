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

describe("Data Integration imports delete permission", () => {
  it("uses canonical imports delete permission", () => {
    expect(permissionSource).toContain('IMPORT_PERMISSION_DELETE = "fair_crm.imports.delete"');
    expect(source).toContain("const canDelete = can(IMPORT_PERMISSION_DELETE)");
  });

  it("hides and fails closed delete without delete permission", () => {
    expect(source).toContain("if (!canDelete || !batchToDelete) return;");
    expect(source).toContain("handlers.canDelete ? (");
    expect(source).toContain("canDelete && batchToDelete ? (");
  });
});
