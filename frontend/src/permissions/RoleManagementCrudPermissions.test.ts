import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/RoleManagementPage.tsx", import.meta.url)),
  "utf8",
);

describe("RoleManagementPage organization role permissions", () => {
  it("uses the canonical role CRUD permissions", () => {
    expect(source).toContain('grantedPermissions.has("identity.roles.create")');
    expect(source).toContain('grantedPermissions.has("identity.roles.update")');
    expect(source).toContain('grantedPermissions.has("identity.roles.delete")');
  });

  it("fails closed before opening or submitting role mutations", () => {
    expect(source).toContain("const openCreateRole = () => {\n    if (!canCreateRole) return;");
    expect(source).toContain("if (editing ? !canUpdateRole : !canCreateRole) return;");
  });

  it("fails closed before deleting an organization role", () => {
    expect(source).toContain("if (!organizationId || !canDeleteRole) return;");
  });
});
