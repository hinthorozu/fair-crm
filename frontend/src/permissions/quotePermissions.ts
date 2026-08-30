import {
  getGrantedCorePermissions,
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "./corePermissions";

export const QUOTE_READ = "fair_crm.quotes.read";
export const QUOTE_CREATE = "fair_crm.quotes.create";
export const QUOTE_UPDATE = "fair_crm.quotes.update";

export const QUOTE_EDITOR_READ_REQUIREMENTS = [
  "fair_crm.todos.read",
  "fair_crm.customers.read",
  "fair_crm.fairs.read",
  QUOTE_READ,
  "fair_crm.quote_templates.read",
  "fair_crm.template_contents.read",
] as const;

export function canReadQuoteEditor(granted: GrantedPermissionCollection): boolean {
  return QUOTE_EDITOR_READ_REQUIREMENTS.every((permissionCode) =>
    hasGrantedCorePermission(granted, permissionCode),
  );
}

export function getQuotePermissions(): Set<string> {
  return getGrantedCorePermissions();
}
