import { describe, expect, it } from "vitest";
import {
  canAccessAdminSection,
  canAccessApplicationPath,
  canAccessMainNavigation,
  firstAccessibleAdminPath,
  PERMISSION_COST_CATEGORIES_CREATE,
  PERMISSION_COST_PRODUCTS_CREATE,
  PERMISSION_COST_PRODUCTS_DELETE,
  PERMISSION_COST_PRODUCTS_UPDATE,
  resolvePermissionLandingPath,
} from "./navigationPermissions";

const granted = (...permissions: string[]) => new Set(permissions);

describe("cost catalog navigation permissions", () => {
  it("lets a category create-only user reach the cost catalog", () => {
    const permissions = granted(PERMISSION_COST_CATEGORIES_CREATE);

    expect(canAccessMainNavigation("/admin", permissions)).toBe(true);
    expect(canAccessAdminSection("cost-catalog", permissions)).toBe(true);
    expect(canAccessApplicationPath("/admin/cost-catalog", permissions)).toBe(true);
    expect(firstAccessibleAdminPath(permissions)).toBe("/admin/cost-catalog");
    expect(resolvePermissionLandingPath("/admin", permissions)).toBe("/admin/cost-catalog");
  });

  it("lets a product create-only user reach the cost catalog", () => {
    const permissions = granted(PERMISSION_COST_PRODUCTS_CREATE);

    expect(canAccessMainNavigation("/admin", permissions)).toBe(true);
    expect(canAccessAdminSection("cost-catalog", permissions)).toBe(true);
    expect(canAccessApplicationPath("/admin/cost-catalog", permissions)).toBe(true);
    expect(resolvePermissionLandingPath("/admin", permissions)).toBe("/admin/cost-catalog");
  });

  it("treats existing update/delete permissions as belonging to the same admin section", () => {
    expect(
      canAccessAdminSection("cost-catalog", granted(PERMISSION_COST_PRODUCTS_UPDATE)),
    ).toBe(true);
    expect(
      canAccessAdminSection("cost-catalog", granted(PERMISSION_COST_PRODUCTS_DELETE)),
    ).toBe(true);
  });
});
