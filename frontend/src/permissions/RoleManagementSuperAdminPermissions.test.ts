import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/RoleManagementPage.tsx", import.meta.url)),
  "utf8",
);

describe("RoleManagementPage SuperAdmin boundaries", () => {
  it("fails closed for role-template mutations and sync", () => {
    expect(source).toContain("const saveTemplate = async (template: ManagedRole) => {\n    if (!isSuperAdmin) return;");
    expect(source).toContain("event.preventDefault();\n    if (!isSuperAdmin) return;\n    if (!deriveSource || !organizationId) return;");
    expect(source).toContain("const requestSync = async (role: ManagedRole) => {\n    if (!isSuperAdmin) return;");
    expect(source).toContain("const confirmSync = async () => {\n    if (!isSuperAdmin) return;");
  });

  it("fails closed for permission lifecycle preview and execution", () => {
    expect(source).toContain('state: RolePermission["lifecycle_state"],\n  ) => {\n    if (!isSuperAdmin) return;');
    expect(source).toContain("const confirmPermissionStateChange = async () => {\n    if (!isSuperAdmin) return;");
  });
});
