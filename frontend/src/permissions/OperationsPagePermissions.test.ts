import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/OperationsPage.tsx", import.meta.url)),
  "utf8",
);

const navigationPermissionSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Operations new action permission", () => {
  it("uses the canonical operations create permission", () => {
    expect(navigationPermissionSource).toContain(
      'PERMISSION_OPERATIONS_CREATE = "fair_crm.operations.create"',
    );
  });

  it("hides and fails closed the new operation entry point without create permission", () => {
    expect(source).toContain("const canCreate = can(PERMISSION_OPERATIONS_CREATE)");
    expect(source).toContain("canCreate ? (");
    expect(source).toContain("open={canCreate && typeModalOpen}");
    expect(source).toContain("if (!canCreate) return;");
  });
});
