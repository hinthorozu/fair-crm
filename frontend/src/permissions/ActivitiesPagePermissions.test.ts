import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/ActivitiesPage.tsx", import.meta.url)),
  "utf8",
);

const permissionSource = readFileSync(
  fileURLToPath(new URL("./activityPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Activities page permission-controlled surfaces", () => {
  it("uses the canonical Core activity delete permission", () => {
    expect(permissionSource).toContain('ACTIVITY_DELETE = "fair_crm.activities.delete"');
    expect(source).toContain("const canDelete = can(ACTIVITY_DELETE)");
  });

  it("hides selection, single delete and bulk delete without delete permission", () => {
    expect(source).toContain("const selectedCount = canDelete ? rowSelection.selectedIds.size : 0");
    expect(source).toContain("canDelete && selectedCount > 0");
    expect(source).toContain("rowSelection={\n          canDelete");
    expect(source).toContain("{canDelete ? (\n              <button");
    expect(source).toContain('canDelete && confirm?.type === "single"');
    expect(source).toContain('canDelete && confirm?.type === "bulk"');
    expect(source).toContain("if (!canDelete) return;");
  });

  it("does not fetch or expose customer navigation/filtering without customer read permission", () => {
    expect(source).toContain("const canReadCustomers = can(CUSTOMER_READ)");
    expect(source).toContain("if (!canReadCustomers) {");
    expect(source).toContain("if (canReadCustomers && customerId && onOpenCustomer)");
    expect(source).toContain("{canReadCustomers ? (\n              <SelectInput");
    expect(source).toContain("onOpenCustomer={canReadCustomers ? onOpenCustomer : undefined}");
  });

  it("clears pending destructive UI state if delete permission disappears", () => {
    expect(source).toContain("rowSelection.clearSelection();\n    setConfirm(null);");
    expect(source).toContain("[canDelete, rowSelection.clearSelection]");
  });
});
