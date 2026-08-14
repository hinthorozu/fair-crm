import { getGrantedCorePermissions } from "./corePermissions";

export const QUOTE_TEMPLATE_PERMISSION_READ = "fair_crm.quote_templates.read";
export const QUOTE_TEMPLATE_PERMISSION_CREATE = "fair_crm.quote_templates.create";
export const QUOTE_TEMPLATE_PERMISSION_UPDATE = "fair_crm.quote_templates.update";
export const QUOTE_TEMPLATE_PERMISSIONS_ALL = [
  QUOTE_TEMPLATE_PERMISSION_READ,
  QUOTE_TEMPLATE_PERMISSION_CREATE,
  QUOTE_TEMPLATE_PERMISSION_UPDATE,
] as const;

export function getGrantedQuoteTemplatePermissions(): Set<string> {
  return getGrantedCorePermissions();
}

export function hasQuoteTemplatePermission(permission: string): boolean {
  return getGrantedQuoteTemplatePermissions().has(permission);
}
