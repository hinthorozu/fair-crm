import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/FairsPage.tsx", import.meta.url)),
  "utf8",
);

const fairPermissionSource = readFileSync(
  fileURLToPath(new URL("./fairPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Fairs list permission-controlled actions", () => {
  it("uses the canonical Core fair CRUD permission codes", () => {
    expect(fairPermissionSource).toContain('FAIR_CREATE = "fair_crm.fairs.create"');
    expect(fairPermissionSource).toContain('FAIR_UPDATE = "fair_crm.fairs.update"');
    expect(fairPermissionSource).toContain('FAIR_DELETE = "fair_crm.fairs.delete"');
  });

  it("hides create, edit, archive and restore entry points independently", () => {
    expect(source).toContain("const canCreate = can(FAIR_CREATE)");
    expect(source).toContain("const canUpdate = can(FAIR_UPDATE)");
    expect(source).toContain("const canDelete = can(FAIR_DELETE)");
    expect(source).toContain("canCreate ? (");
    expect(source).toContain("onCreate={canCreate ? openCreate : undefined}");
    expect(source).toContain("canUpdate\n              ? (fair) => {");
    expect(source).toContain('onArchive={canDelete ? (fair) => setConfirm({ type: "archive", fair }) : undefined}');
    expect(source).toContain('onRestore={canDelete ? (fair) => setConfirm({ type: "restore", fair }) : undefined}');
  });

  it("also fails closed if permission state changes while a modal or confirmation is open", () => {
    expect(source).toContain('modal === "create" && canCreate');
    expect(source).toContain('modal === "edit" && editing && canUpdate');
    expect(source).toContain('confirm?.type === "archive" && canDelete');
    expect(source).toContain('confirm?.type === "restore" && canDelete');
  });
});
