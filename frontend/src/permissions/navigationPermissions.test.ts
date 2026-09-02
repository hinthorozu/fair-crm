import { describe, expect, it } from "vitest";
import { FAIR_EMAIL_PERMISSION_EXECUTE } from "./fairEmailPermissions";
import { SCRAPER_PERMISSION_EXECUTE } from "./scraperPermissions";
import {
  canAccessAdminSection,
  canAccessApplicationPath,
  canAccessDataIntegrationSection,
  canAccessMainNavigation,
  firstAccessibleAdminPath,
  firstAccessibleDataIntegrationPath,
  PERMISSION_BACKUPS_READ,
  PERMISSION_CUSTOMERS_READ,
  PERMISSION_EMAIL_ACCOUNTS_READ,
  PERMISSION_FAIRS_READ,
  PERMISSION_IMPORTS_CREATE,
  PERMISSION_IMPORTS_READ,
  PERMISSION_MAIL_SEND_OPERATIONS_READ,
  PERMISSION_OPERATIONS_CREATE,
  PERMISSION_OPERATIONS_READ,
  PERMISSION_SCRAPER_READ,
  PERMISSION_USERS_READ,
  resolvePermissionLandingPath,
  resolvePermissionSectionLandingPath,
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
    expect(resolvePermissionLandingPath("/admin", readUser)).toBe("/admin/system/users");

    const superAdminEffectivePermissions = granted(PERMISSION_BACKUPS_READ);
    expect(canAccessAdminSection("backups", superAdminEffectivePermissions)).toBe(true);
    expect(canAccessApplicationPath("/admin", superAdminEffectivePermissions)).toBe(true);
    expect(resolvePermissionLandingPath("/admin/", superAdminEffectivePermissions)).toBe(
      "/admin/system/backups",
    );
    expect(resolvePermissionLandingPath("/admin", granted())).toBeNull();
  });

  it("uses dedicated mail operation read permission instead of email account read", () => {
    const emailAccountReader = granted(PERMISSION_EMAIL_ACCOUNTS_READ);
    expect(canAccessAdminSection("email-accounts", emailAccountReader)).toBe(true);
    expect(canAccessAdminSection("mail-operations", emailAccountReader)).toBe(false);
    expect(
      canAccessApplicationPath("/admin/smtp-operations/mail-operations", emailAccountReader),
    ).toBe(false);

    const mailOperationReader = granted(PERMISSION_MAIL_SEND_OPERATIONS_READ);
    expect(canAccessMainNavigation("/admin", mailOperationReader)).toBe(true);
    expect(canAccessAdminSection("mail-operations", mailOperationReader)).toBe(true);
    expect(canAccessAdminSection("email-accounts", mailOperationReader)).toBe(false);
    expect(
      canAccessApplicationPath("/admin/smtp-operations/mail-operations", mailOperationReader),
    ).toBe(true);
    expect(resolvePermissionLandingPath("/admin", mailOperationReader)).toBe(
      "/admin/smtp-operations/mail-operations",
    );
  });

  it("separates operation read routes from the generic operation creation route", () => {
    const reader = granted(PERMISSION_OPERATIONS_READ);
    expect(canAccessApplicationPath("/operations", reader)).toBe(true);
    expect(canAccessApplicationPath("/operations/abc", reader)).toBe(true);
    expect(canAccessApplicationPath("/operations/new", reader)).toBe(false);

    const creator = granted(PERMISSION_OPERATIONS_READ, PERMISSION_OPERATIONS_CREATE);
    expect(canAccessApplicationPath("/operations/new", creator)).toBe(true);
  });

  it("uses canonical business permissions for specialized operation wizard routes", () => {
    expect(
      canAccessApplicationPath("/operations/new/bulk-email", granted(FAIR_EMAIL_PERMISSION_EXECUTE)),
    ).toBe(true);
    expect(
      canAccessApplicationPath("/operations/new/enrichment", granted(SCRAPER_PERMISSION_EXECUTE)),
    ).toBe(false);
    expect(
      canAccessApplicationPath(
        "/operations/new/enrichment",
        granted(SCRAPER_PERMISSION_EXECUTE, PERMISSION_SCRAPER_READ),
      ),
    ).toBe(true);
    expect(
      canAccessApplicationPath("/operations/new/scraper", granted(SCRAPER_PERMISSION_EXECUTE)),
    ).toBe(false);
    expect(
      canAccessApplicationPath(
        "/operations/new/scraper",
        granted(SCRAPER_PERMISSION_EXECUTE, PERMISSION_FAIRS_READ),
      ),
    ).toBe(false);
    expect(
      canAccessApplicationPath(
        "/operations/new/scraper",
        granted(SCRAPER_PERMISSION_EXECUTE, PERMISSION_SCRAPER_READ),
      ),
    ).toBe(false);
    expect(
      canAccessApplicationPath(
        "/operations/new/scraper",
        granted(
          SCRAPER_PERMISSION_EXECUTE,
          PERMISSION_FAIRS_READ,
          PERMISSION_SCRAPER_READ,
        ),
      ),
    ).toBe(true);

    const genericCreator = granted(PERMISSION_OPERATIONS_CREATE);
    expect(canAccessApplicationPath("/operations/new/bulk-email", genericCreator)).toBe(false);
    expect(canAccessApplicationPath("/operations/new/enrichment", genericCreator)).toBe(false);
    expect(canAccessApplicationPath("/operations/new/scraper", genericCreator)).toBe(false);
    expect(canAccessApplicationPath("/operations/new", genericCreator)).toBe(true);
    expect(canAccessApplicationPath("/operations/new/custom", genericCreator)).toBe(true);
  });

  it("separates import read, create and scraper surfaces", () => {
    const importReader = granted(PERMISSION_IMPORTS_READ);
    expect(canAccessDataIntegrationSection("imports", importReader)).toBe(true);
    expect(canAccessDataIntegrationSection("new", importReader)).toBe(false);
    expect(canAccessApplicationPath("/data-integration", importReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration/imports/new", importReader)).toBe(false);
    expect(firstAccessibleDataIntegrationPath(importReader)).toBe("/data-integration/imports");
    expect(resolvePermissionLandingPath("/data-integration", importReader)).toBe(
      "/data-integration/imports",
    );

    const importCreator = granted(PERMISSION_IMPORTS_CREATE);
    expect(canAccessMainNavigation("/data-integration", importCreator)).toBe(true);
    expect(canAccessDataIntegrationSection("new", importCreator)).toBe(true);
    expect(canAccessApplicationPath("/imports", importCreator)).toBe(true);
    expect(resolvePermissionLandingPath("/data-integration/", importCreator)).toBe(
      "/data-integration/imports/new",
    );

    const scraperReader = granted(PERMISSION_SCRAPER_READ);
    expect(canAccessMainNavigation("/data-integration", scraperReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration", scraperReader)).toBe(false);
    expect(canAccessDataIntegrationSection("adapters", scraperReader)).toBe(true);
    expect(canAccessApplicationPath("/data-integration/adapters", scraperReader)).toBe(true);
    expect(firstAccessibleDataIntegrationPath(scraperReader)).toBe("/data-integration/adapters");
    expect(resolvePermissionLandingPath("/data-integration", scraperReader)).toBe(
      "/data-integration/adapters",
    );
    expect(resolvePermissionLandingPath("/data-integration", granted())).toBeNull();
  });

  it("resolves section breadcrumb landings from effective permissions", () => {
    expect(
      resolvePermissionSectionLandingPath("/admin/system/users", granted(PERMISSION_USERS_READ)),
    ).toBe("/admin/system/users");
    expect(
      resolvePermissionSectionLandingPath(
        "/admin/smtp-operations/mail-operations",
        granted(PERMISSION_MAIL_SEND_OPERATIONS_READ),
      ),
    ).toBe("/admin/smtp-operations/mail-operations");
    expect(
      resolvePermissionSectionLandingPath(
        "/data-integration/run-history?adapter_key=x",
        granted(PERMISSION_SCRAPER_READ),
      ),
    ).toBe("/data-integration/adapters");
    expect(
      resolvePermissionSectionLandingPath(
        "/data-integration/imports/new",
        granted(PERMISSION_IMPORTS_CREATE),
      ),
    ).toBe("/data-integration/imports/new");
    expect(
      resolvePermissionSectionLandingPath("/admin/data-operations", granted(PERMISSION_USERS_READ)),
    ).toBeNull();
    expect(
      resolvePermissionSectionLandingPath("/customers", granted(PERMISSION_USERS_READ)),
    ).toBeNull();
    expect(resolvePermissionSectionLandingPath("/admin/system/users", granted())).toBeNull();
  });

  it("does not synthesize landing paths for non-root application routes", () => {
    expect(resolvePermissionLandingPath("/customers", granted(PERMISSION_CUSTOMERS_READ))).toBeNull();
    expect(resolvePermissionLandingPath("/admin/system/users", granted(PERMISSION_USERS_READ))).toBeNull();
  });

  it("fails closed for unknown application paths and permits dev bypass explicitly", () => {
    expect(canAccessApplicationPath("/unknown-protected-route", granted())).toBe(false);
    expect(canAccessApplicationPath("/unknown-protected-route", granted(), true)).toBe(true);
  });
});
