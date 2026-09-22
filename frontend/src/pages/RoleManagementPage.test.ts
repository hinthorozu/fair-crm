import { describe, expect, it } from "vitest";

import { groupTitle, permissionGroup, samePermissionIds } from "./RoleManagementPage";

describe("RoleManagementPage helpers", () => {
  it("groups CRUD permissions by product and module", () => {
    expect(permissionGroup("fair_crm.customers.create")).toBe("fair_crm.customers");
    expect(permissionGroup("identity.roles.update")).toBe("identity.roles");
    expect(permissionGroup("fair_crm.fair_stand.projects.read")).toBe("fair_crm.fair_stand");
  });

  it("titles known permission groups in Turkish", () => {
    expect(groupTitle("fair_crm.fair_stand")).toBe("Fair Stand Projeleri");
    expect(groupTitle("fair_crm.admin")).toBe("Sistem Yönetimi");
    expect(groupTitle("unknown.module")).toBe("unknown.module");
  });

  it("compares permission selections without depending on checkbox order", () => {
    expect(samePermissionIds(["permission-a", "permission-b"], ["permission-b", "permission-a"])).toBe(true);
    expect(samePermissionIds(["permission-a"], ["permission-a", "permission-b"])).toBe(false);
    expect(samePermissionIds(["permission-a"], ["permission-b"])).toBe(false);
  });
});
