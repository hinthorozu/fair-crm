import { describe, expect, it } from "vitest";

import { permissionGroup, samePermissionIds } from "./RoleManagementPage";

describe("RoleManagementPage helpers", () => {
  it("groups CRUD permissions by product and module", () => {
    expect(permissionGroup("fair_crm.customers.create")).toBe("fair_crm.customers");
    expect(permissionGroup("identity.roles.update")).toBe("identity.roles");
  });

  it("compares permission selections without depending on checkbox order", () => {
    expect(samePermissionIds(["permission-a", "permission-b"], ["permission-b", "permission-a"])).toBe(true);
    expect(samePermissionIds(["permission-a"], ["permission-a", "permission-b"])).toBe(false);
    expect(samePermissionIds(["permission-a"], ["permission-b"])).toBe(false);
  });
});
