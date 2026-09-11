import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/UsersAdminPage.tsx", import.meta.url)),
  "utf8",
);

describe("Users admin supporting role read permissions", () => {
  it("keeps users.read page hydration independent from roles.read", () => {
    expect(source).toContain("PERMISSION_ROLES_READ");
    expect(source).toContain(
      "const canReadRoles = actorIsSuperAdmin || grantedPermissions.has(PERMISSION_ROLES_READ)",
    );
    expect(source).toContain("const userResult = await listManagedUsers(organizationId)");
    expect(source).toContain("if (canReadRoles) {");
    expect(source).toContain("const roleResult = await listAssignableRoles(organizationId)");
    expect(source).not.toContain("const [userResult, roleResult] = await Promise.all([");
  });

  it("fails closed for role-dependent creation while preserving user editing", () => {
    expect(source).toContain("if (!canCreateUsers || !canReadRoles) return;");
    expect(source).toContain(
      "const canOfferCreate = canCreateUsers && canReadRoles && Boolean(organizationId) && roles.length > 0",
    );
    expect(source).toContain(
      '{canReadRoles ? <label className="form-field"><span className="form-label">Rol',
    );
    expect(source).toContain(
      ': editing && !form.isSuperAdmin ? <div className="form-field"><span className="form-label">Rol</span><strong>{editing.role?.name ?? "—"}</strong></div> : null}',
    );
  });

  it("does not reassign the current role for unrelated user updates", () => {
    expect(source).toContain(
      'const roleChanged = form.roleId !== (editing.role?.id ?? "")',
    );
    expect(source).toContain(
      "...(canReadRoles && !form.isSuperAdmin && roleChanged ? { role_id: form.roleId } : {})",
    );
  });
});
