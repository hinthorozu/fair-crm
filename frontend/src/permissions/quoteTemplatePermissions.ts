import { config } from "../config";

export const QUOTE_TEMPLATE_PERMISSION_READ = "fair_crm.quote_templates.read";
export const QUOTE_TEMPLATE_PERMISSION_CREATE = "fair_crm.quote_templates.create";
export const QUOTE_TEMPLATE_PERMISSION_UPDATE = "fair_crm.quote_templates.update";
export const QUOTE_TEMPLATE_PERMISSIONS_ALL = [
  QUOTE_TEMPLATE_PERMISSION_READ,
  QUOTE_TEMPLATE_PERMISSION_CREATE,
  QUOTE_TEMPLATE_PERMISSION_UPDATE,
] as const;

export function getGrantedQuoteTemplatePermissions(): Set<string> {
  if (config.devBypassEnabled) return new Set(QUOTE_TEMPLATE_PERMISSIONS_ALL);
  const raw = import.meta.env.VITE_GRANTED_PERMISSIONS as string | undefined;
  if (!raw?.trim()) return new Set(QUOTE_TEMPLATE_PERMISSIONS_ALL);
  return new Set(raw.split(",").map((item) => item.trim()).filter(Boolean));
}

export function hasQuoteTemplatePermission(permission: string): boolean {
  return getGrantedQuoteTemplatePermissions().has(permission);
}
