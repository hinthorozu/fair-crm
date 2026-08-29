import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/UsersAdminPage.tsx", import.meta.url)),
  "utf8",
);

describe("P0.2 Super Admin user-management UI compatibility", () => {
  it("keeps the existing manual create entry and requires an admin-supplied password", () => {
    expect(source).toContain('>Yeni Kullanıcı</button>');
    expect(source).toContain('if (!editing && !form.password)');
    expect(source).toContain('setFormError("Şifre zorunludur.")');
    expect(source).toContain('required={!editing}');
    expect(source).toContain('password: form.password');
    expect(source).toContain('createManagedUser(organizationId');
  });

  it("keeps role and Super Admin controls backend-authoritative", () => {
    expect(source).toContain('setCanManageSuperAdmin(userResult.can_manage_super_admin)');
    expect(source).toContain('{canManageSuperAdmin ? <label className="form-field"><span className="form-label">Super Admin</span>');
    expect(source).toContain('...(canManageSuperAdmin ? { is_super_admin: form.isSuperAdmin } : {})');
    expect(source).toContain('if (!form.isSuperAdmin && !form.roleId)');
  });

  it("does not expose an unsupported setup-link creation mode", () => {
    const normalized = source.toLowerCase();
    expect(normalized).not.toContain("setup link");
    expect(normalized).not.toContain("setup_link");
    expect(normalized).not.toContain("kurulum bağlantısı");
  });
});
