import {
  hasAnyGrantedCorePermission,
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";
import { FAIR_EMAIL_PERMISSION_EXECUTE } from "./fairEmailPermissions";
import { OPERATION_EXECUTE } from "./operationPermissions";
import { canReadQuoteEditor } from "./quotePermissions";
import { SCRAPER_PERMISSION_EXECUTE } from "./scraperPermissions";

export const PERMISSION_ORGANIZATIONS_READ = "identity.organizations.read";
export const PERMISSION_ORGANIZATIONS_UPDATE = "identity.organizations.update";
export const PERMISSION_ORGANIZATIONS_SYSTEM = "identity.organizations.delete";
export const PERMISSION_USERS_READ = "identity.users.read";
export const PERMISSION_USERS_CREATE = "identity.users.create";
export const PERMISSION_USERS_UPDATE = "identity.users.update";
export const PERMISSION_USERS_DELETE = "identity.users.delete";
export const PERMISSION_ROLES_READ = "identity.roles.read";

export const PERMISSION_CUSTOMERS_READ = "fair_crm.customers.read";
export const PERMISSION_FAIRS_READ = "fair_crm.fairs.read";
export const PERMISSION_TODOS_READ = "fair_crm.todos.read";
export const PERMISSION_OPERATIONS_READ = "fair_crm.operations.read";
export const PERMISSION_OPERATIONS_CREATE = "fair_crm.operations.create";
export const PERMISSION_DATA_OPERATIONS_READ = "fair_crm.admin.data_operations.read";
export const PERMISSION_ACTIVITIES_READ = "fair_crm.activities.read";
export const PERMISSION_IMPORTS_READ = "fair_crm.imports.read";
export const PERMISSION_IMPORTS_CREATE = "fair_crm.imports.create";
export const PERMISSION_IMPORTS_UPDATE = "fair_crm.imports.update";
export const PERMISSION_SCRAPER_READ = "fair_crm.scraper.read";
export const PERMISSION_BACKUPS_READ = "fair_crm.admin.backups.read";
export const PERMISSION_EMAIL_ACCOUNTS_READ = "fair_crm.email_accounts.read";
export const PERMISSION_MAIL_SEND_OPERATIONS_READ = "fair_crm.mail_send_operations.read";
export const PERMISSION_MAIL_TEMPLATES_READ = "fair_crm.mail_templates.read";
export const PERMISSION_QUOTE_TEMPLATES_READ = "fair_crm.quote_templates.read";
export const PERMISSION_TEMPLATE_CONTENTS_READ = "fair_crm.template_contents.read";
export const PERMISSION_COST_CATEGORIES_READ = "fair_crm.cost_catalog.categories.read";
export const PERMISSION_COST_CATEGORIES_CREATE = "fair_crm.cost_catalog.categories.create";
export const PERMISSION_COST_CATEGORIES_UPDATE = "fair_crm.cost_catalog.categories.update";
export const PERMISSION_COST_CATEGORIES_DELETE = "fair_crm.cost_catalog.categories.delete";
export const PERMISSION_COST_PRODUCTS_READ = "fair_crm.cost_catalog.products.read";
export const PERMISSION_COST_PRODUCTS_CREATE = "fair_crm.cost_catalog.products.create";
export const PERMISSION_COST_PRODUCTS_UPDATE = "fair_crm.cost_catalog.products.update";
export const PERMISSION_COST_PRODUCTS_DELETE = "fair_crm.cost_catalog.products.delete";

export const COST_CATALOG_ADMIN_PERMISSIONS = [
  PERMISSION_COST_CATEGORIES_READ,
  PERMISSION_COST_CATEGORIES_CREATE,
  PERMISSION_COST_CATEGORIES_UPDATE,
  PERMISSION_COST_CATEGORIES_DELETE,
  PERMISSION_COST_PRODUCTS_READ,
  PERMISSION_COST_PRODUCTS_CREATE,
  PERMISSION_COST_PRODUCTS_UPDATE,
  PERMISSION_COST_PRODUCTS_DELETE,
] as const;

export type PermissionRequirement =
  | { kind: "public" }
  | { kind: "permission"; permission: string }
  | { kind: "all"; permissions: readonly string[] }
  | { kind: "any"; permissions: readonly string[] }
  | { kind: "anyRequirement"; requirements: readonly PermissionRequirement[] };

export const MAIN_NAV_REQUIREMENTS: Readonly<Record<string, PermissionRequirement>> = {
  "/dashboard": { kind: "public" },
  "/customers": { kind: "permission", permission: PERMISSION_CUSTOMERS_READ },
  "/fairs": { kind: "permission", permission: PERMISSION_FAIRS_READ },
  "/todos": { kind: "permission", permission: PERMISSION_TODOS_READ },
  "/operations": { kind: "permission", permission: PERMISSION_OPERATIONS_READ },
  "/activities": { kind: "permission", permission: PERMISSION_ACTIVITIES_READ },
  "/data-integration": {
    kind: "anyRequirement",
    requirements: [
      { kind: "permission", permission: PERMISSION_IMPORTS_READ },
      {
        kind: "all",
        permissions: [PERMISSION_IMPORTS_CREATE, PERMISSION_FAIRS_READ],
      },
      { kind: "permission", permission: PERMISSION_SCRAPER_READ },
    ],
  },
  "/admin": {
    kind: "any",
    permissions: [
      PERMISSION_ORGANIZATIONS_READ,
      PERMISSION_USERS_READ,
      PERMISSION_ROLES_READ,
      PERMISSION_BACKUPS_READ,
      PERMISSION_EMAIL_ACCOUNTS_READ,
      PERMISSION_MAIL_SEND_OPERATIONS_READ,
      PERMISSION_MAIL_TEMPLATES_READ,
      PERMISSION_QUOTE_TEMPLATES_READ,
      PERMISSION_TEMPLATE_CONTENTS_READ,
      PERMISSION_OPERATIONS_READ,
      ...COST_CATALOG_ADMIN_PERMISSIONS,
    ],
  },
};

export const ADMIN_NAV_REQUIREMENTS: Readonly<Record<string, PermissionRequirement>> = {
  organizations: { kind: "permission", permission: PERMISSION_ORGANIZATIONS_READ },
  users: { kind: "permission", permission: PERMISSION_USERS_READ },
  roles: { kind: "permission", permission: PERMISSION_ROLES_READ },
  backups: { kind: "permission", permission: PERMISSION_BACKUPS_READ },
  "cost-catalog": {
    kind: "any",
    permissions: COST_CATALOG_ADMIN_PERMISSIONS,
  },
  "email-accounts": { kind: "permission", permission: PERMISSION_EMAIL_ACCOUNTS_READ },
  "mail-templates": { kind: "permission", permission: PERMISSION_MAIL_TEMPLATES_READ },
  "quote-templates": { kind: "permission", permission: PERMISSION_QUOTE_TEMPLATES_READ },
  "template-contents": { kind: "permission", permission: PERMISSION_TEMPLATE_CONTENTS_READ },
  "mail-operations": { kind: "permission", permission: PERMISSION_MAIL_SEND_OPERATIONS_READ },
  "operation-capabilities": { kind: "permission", permission: PERMISSION_OPERATIONS_READ },
};

export const DATA_INTEGRATION_NAV_REQUIREMENTS: Readonly<
  Record<string, PermissionRequirement>
> = {
  imports: { kind: "permission", permission: PERMISSION_IMPORTS_READ },
  new: {
    kind: "all",
    permissions: [PERMISSION_IMPORTS_CREATE, PERMISSION_FAIRS_READ],
  },
  jobs: { kind: "permission", permission: PERMISSION_IMPORTS_READ },
  reports: { kind: "permission", permission: PERMISSION_IMPORTS_READ },
  adapters: { kind: "permission", permission: PERMISSION_SCRAPER_READ },
  "run-history": { kind: "permission", permission: PERMISSION_SCRAPER_READ },
  "scraper-test": { kind: "permission", permission: PERMISSION_SCRAPER_READ },
};

export function satisfiesPermissionRequirement(
  granted: GrantedPermissionCollection,
  requirement: PermissionRequirement,
  bypass = false,
): boolean {
  if (bypass || requirement.kind === "public") return true;
  if (requirement.kind === "permission") {
    return hasGrantedCorePermission(granted, requirement.permission);
  }
  if (requirement.kind === "all") {
    return requirement.permissions.every((permission) =>
      hasGrantedCorePermission(granted, permission),
    );
  }
  if (requirement.kind === "anyRequirement") {
    return requirement.requirements.some((nested) =>
      satisfiesPermissionRequirement(granted, nested),
    );
  }
  return hasAnyGrantedCorePermission(granted, requirement.permissions);
}

export function canAccessAdminSection(
  section: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): boolean {
  const requirement = ADMIN_NAV_REQUIREMENTS[section];
  return requirement ? satisfiesPermissionRequirement(granted, requirement, bypass) : false;
}

export function canAccessDataIntegrationSection(
  section: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): boolean {
  const requirement = DATA_INTEGRATION_NAV_REQUIREMENTS[section];
  return requirement ? satisfiesPermissionRequirement(granted, requirement, bypass) : false;
}

export function canAccessMainNavigation(
  sectionPath: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): boolean {
  const requirement = MAIN_NAV_REQUIREMENTS[sectionPath];
  return requirement ? satisfiesPermissionRequirement(granted, requirement, bypass) : false;
}

export function firstAccessibleAdminPath(
  granted: GrantedPermissionCollection,
  bypass = false,
): string | null {
  const candidates: Array<[string, string]> = [
    ["organizations", "/admin/system/organizations"],
    ["users", "/admin/system/users"],
    ["roles", "/admin/system/roles"],
    ["backups", "/admin/system/backups"],
    ["cost-catalog", "/admin/cost-catalog"],
    ["email-accounts", "/admin/email-accounts"],
    ["mail-templates", "/admin/smtp-operations/templates"],
    ["quote-templates", "/admin/smtp-operations/quote-templates"],
    ["template-contents", "/admin/smtp-operations/template-contents"],
    ["mail-operations", "/admin/smtp-operations/mail-operations"],
    ["operation-capabilities", "/admin/operation-capabilities"],
  ];
  return candidates.find(([section]) => canAccessAdminSection(section, granted, bypass))?.[1] ?? null;
}

export function firstAccessibleDataIntegrationPath(
  granted: GrantedPermissionCollection,
  bypass = false,
): string | null {
  const candidates: Array<[string, string]> = [
    ["imports", "/data-integration/imports"],
    ["new", "/data-integration/imports/new"],
    ["adapters", "/data-integration/adapters"],
    ["run-history", "/data-integration/run-history"],
    ["scraper-test", "/data-integration/scraper-test"],
  ];
  return (
    candidates.find(([section]) => canAccessDataIntegrationSection(section, granted, bypass))?.[1] ??
    null
  );
}

function normalizePath(path: string): string {
  const queryIndex = path.indexOf("?");
  const pathname = (queryIndex >= 0 ? path.slice(0, queryIndex) : path).replace(/\/$/, "");
  return pathname || "/";
}

export function resolvePermissionLandingPath(
  path: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): string | null {
  const pathname = normalizePath(path);
  if (pathname === "/admin") return firstAccessibleAdminPath(granted, bypass);
  if (pathname === "/data-integration") {
    return firstAccessibleDataIntegrationPath(granted, bypass);
  }
  return null;
}

export function resolvePermissionSectionLandingPath(
  path: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): string | null {
  const pathname = normalizePath(path);
  if (
    pathname === "/admin" ||
    (pathname.startsWith("/admin/") && !pathname.startsWith("/admin/data-operations"))
  ) {
    return firstAccessibleAdminPath(granted, bypass);
  }
  if (pathname === "/data-integration" || pathname.startsWith("/data-integration/")) {
    return firstAccessibleDataIntegrationPath(granted, bypass);
  }
  return null;
}

export function canAccessApplicationPath(
  path: string,
  granted: GrantedPermissionCollection,
  bypass = false,
): boolean {
  if (bypass) return true;
  const pathname = normalizePath(path);

  if (pathname === "/" || pathname === "/login" || pathname === "/dashboard") return true;

  if (pathname === "/customers" || pathname.startsWith("/customers/")) {
    return hasGrantedCorePermission(granted, PERMISSION_CUSTOMERS_READ);
  }
  if (pathname === "/fairs" || pathname.startsWith("/fairs/")) {
    return hasGrantedCorePermission(granted, PERMISSION_FAIRS_READ);
  }
  if (/^\/todos\/[^/]+\/quote$/.test(pathname)) {
    return canReadQuoteEditor(granted);
  }
  if (pathname === "/todos" || pathname.startsWith("/todos/")) {
    return hasGrantedCorePermission(granted, PERMISSION_TODOS_READ);
  }
  if (pathname === "/activities" || pathname.startsWith("/activities/")) {
    return hasGrantedCorePermission(granted, PERMISSION_ACTIVITIES_READ);
  }

  const canReadDataOperations = hasGrantedCorePermission(granted, PERMISSION_DATA_OPERATIONS_READ);
  if (pathname === "/operations/new/duplicate-check") {
    return hasGrantedCorePermission(granted, OPERATION_EXECUTE) && canReadDataOperations;
  }
  if (pathname === "/operations/new/bulk-email") {
    return hasGrantedCorePermission(granted, FAIR_EMAIL_PERMISSION_EXECUTE);
  }
  if (pathname === "/operations/new/enrichment") {
    return (
      hasGrantedCorePermission(granted, SCRAPER_PERMISSION_EXECUTE) &&
      hasGrantedCorePermission(granted, PERMISSION_SCRAPER_READ)
    );
  }
  if (pathname === "/operations/new/scraper") {
    return (
      hasGrantedCorePermission(granted, SCRAPER_PERMISSION_EXECUTE) &&
      hasGrantedCorePermission(granted, PERMISSION_FAIRS_READ) &&
      hasGrantedCorePermission(granted, PERMISSION_SCRAPER_READ)
    );
  }
  if (pathname.startsWith("/operations/duplicate-check/runs/")) {
    return hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_READ) && canReadDataOperations;
  }
  if (pathname === "/admin/data-operations") {
    return (
      hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_CREATE) && canReadDataOperations
    );
  }
  if (pathname.startsWith("/admin/data-operations/runs/")) {
    return hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_READ) && canReadDataOperations;
  }
  if (pathname.startsWith("/admin/data-operations/")) {
    return (
      hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_CREATE) && canReadDataOperations
    );
  }
  if (pathname === "/operations/new" || pathname.startsWith("/operations/new/")) {
    return hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_CREATE);
  }
  if (pathname === "/operations" || pathname.startsWith("/operations/")) {
    return hasGrantedCorePermission(granted, PERMISSION_OPERATIONS_READ);
  }

  if (pathname === "/data-integration") {
    return hasGrantedCorePermission(granted, PERMISSION_IMPORTS_READ);
  }
  if (pathname === "/imports" || pathname === "/data-integration/imports/new") {
    return (
      hasGrantedCorePermission(granted, PERMISSION_IMPORTS_CREATE) &&
      hasGrantedCorePermission(granted, PERMISSION_FAIRS_READ)
    );
  }
  if (
    pathname.startsWith("/data-integration/imports/fair/") ||
    pathname.startsWith("/imports/fair/")
  ) {
    return hasGrantedCorePermission(granted, PERMISSION_IMPORTS_CREATE);
  }
  if (pathname.startsWith("/data-integration/imports/continue/")) {
    return hasGrantedCorePermission(granted, PERMISSION_IMPORTS_UPDATE);
  }
  if (pathname === "/data-integration/imports") {
    return hasGrantedCorePermission(granted, PERMISSION_IMPORTS_READ);
  }
  if (pathname === "/data-integration/jobs" || pathname === "/data-integration/reports") {
    return hasGrantedCorePermission(granted, PERMISSION_IMPORTS_READ);
  }
  if (
    pathname === "/data-integration/adapters" ||
    pathname.startsWith("/data-integration/adapters/") ||
    pathname === "/data-integration/run-history" ||
    pathname.startsWith("/data-integration/runs/") ||
    pathname === "/data-integration/scraper-test"
  ) {
    return hasGrantedCorePermission(granted, PERMISSION_SCRAPER_READ);
  }

  if (pathname === "/admin") {
    return canAccessAdminSection("backups", granted);
  }
  if (pathname === "/admin/system/organizations") {
    return canAccessAdminSection("organizations", granted);
  }
  if (pathname === "/admin/system/users") return canAccessAdminSection("users", granted);
  if (pathname === "/admin/system/roles") return canAccessAdminSection("roles", granted);
  if (pathname === "/admin/system/backups") return canAccessAdminSection("backups", granted);
  if (pathname === "/admin/cost-catalog") return canAccessAdminSection("cost-catalog", granted);
  if (pathname === "/admin/email-accounts") return canAccessAdminSection("email-accounts", granted);
  if (pathname === "/admin/smtp-operations/templates") {
    return canAccessAdminSection("mail-templates", granted);
  }
  if (pathname === "/admin/smtp-operations/quote-templates") {
    return canAccessAdminSection("quote-templates", granted);
  }
  if (pathname === "/admin/smtp-operations/template-contents") {
    return canAccessAdminSection("template-contents", granted);
  }
  if (pathname === "/admin/smtp-operations/mail-operations") {
    return canAccessAdminSection("mail-operations", granted);
  }
  if (pathname === "/admin/operation-capabilities") {
    return canAccessAdminSection("operation-capabilities", granted);
  }

  return false;
}
