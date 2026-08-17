import { describe, expect, it } from "vitest";
import {
  canAccessAdminSection,
  canAccessApplicationPath,
  canAccessDataIntegrationSection,
  canAccessMainNavigation,
  firstAccessibleAdminPath,
  firstAccessibleDataIntegrationPath,
  PERMISSION_BACKUPS_READ,
  PERMISSION_CUSTOMERS_READ,
  PERMISSION_IMPORTS_CREATE,
  PERMISSION_IMPORTS_READ,
  PERMISSION_OPERATIONS_CREATE,
  PERMISSION_OPERATIONS_READ,
  PERMISSION_SCRAPER_READ,
  PERMISSION_USERS_READ,
} from "./navigationPermissions";

const granted = (...permissions: string[]) => new Set(permissions);

describe("navigation permission rules", () => {
  it("keeps dashboard available without an RBAC permission", () => {
    expect(canAccessApplicationPath("/dashboard", granted())).toBe(true);
    expect(canAccessMainNavigation("/dashboard", granted())).toBe(true);
  });

  it("hides a module and blocks its deep link without read permission", () => {
    expect(canAccessMainNavigation("/customers", granted())).toBe(false);
    expect(canAccessApplicationPath("/customers", granted())).toBe(false);
    expect(canAccessApplicationPath("/customers/123", granted())).toBe(false);

    const permissions = granted(PERMISSION_CUSTOMERS_READ);
    expect(canAccessMainNavigation("/customers", permissions)).toBe(true);
    expect(canAccessApplicationPath("/customers/123", permissions)).toBe(true);
  });

  it("does not show Database Backups to an organization user without the system permission", () => {
    const readUser = granted(PERMISSION_USERS_READ);
    expect(canAccessMainNavigation("/admin", readUser)).toBe(true);
    expect(canAccessAdminSection("users", readUser)).toBe(true);
    expect(canAccessAdminSection("backups", readUser)).toBe(false);
    expect(canAccessApplicationPath("/admin/system/backups", readUser)).toBe(false);
    expect(canAccessApplicationPath("/admin", readUser)).toBe(false);
    expect(firstAccessibleAdminPath(readUser)).toBe("/admin/system/users");

    const superAdminEffectivePermissions = granted(PERMISSION_BACKUPS_READ);
    expect(canAccessAdminSection("backups", superAdminEffectivePermissions)).toBe(true);
    expect(canAccessApplicationPath("/admin", superAdminEffectivePermissions)).toBe(true);
  });

  it("separates operation read routes from operation creation routes", () => {
    const reader = granted(PERMISSION_OPERATIONS_READ);
    expect(canAccessApplicationPath("/operations", reader)).toBe(true);
    expect(canAccessApplicationPath("/operations/abc", reader)).toBe(true);
    expect(canAccessApplicationPath("/operations/new/bulk-email", reader)).toBe(false);

    const creator = granted(PERMISSION_OPERATIONS_READ, PERMISSION_OPERATIONS_CREATE);
    expect(canAccessApplicationPath("/operations/new/bulk-email", creator)).toBe(true);
  });

  it("separates import read, create and scraper surfaces", () => {
    const importReader = granted(PERMISSION_IMPORTS_READ);
    expect(canAccessDataIntegrationSection("imports", importReader)).toBe(true);
    expect(canAccessDataIntegrationSection("new", importReader)).toBe(false);
    expect(canAccessApplicationPath("/data-integration", importReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration/imports/new", importReader)).toBe(false);
    expect(firstAccessibleDataIntegrationPath(importReader)).toBe("/data-integration/imports");

    const importCreator = granted(PERMISSION_IMPORTS_CREATE);
    expect(canAccessDataIntegrationSection("new", importCreator)).toBe(true);
    expect(canAccessApplicationPath("/imports", importCreator)).toBe(true);

    const scraperReader = granted(PERMISSION_SCRAPER_READ);
    expect(canAccessMainNavigation("/data-integration", scraperReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration", scraperReader)).toBe(false);
    expect(canAccessDataIntegrationSection("adapters", scraperReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration/adapters", scraperReader)).toBe(true);
    expect(firstAccessibleDataIntegrationPath(scraperReader)).toBe("/data-integration/adapters");
  });

  it("fails closed for unknown application paths and permits dev bypass explicitly", () => {
    expect(canAccessApplicationPath("/unknown-protected-route", granted())).toBe(false);
    expect(canAccessApplicationPath("/unknown-protected-route", granted(), true)).toBe(true);
  });
});
