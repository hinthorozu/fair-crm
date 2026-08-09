import { config } from "../config";

export const TEMPLATE_CONTENT_PERMISSION_READ = "fair_crm.template_contents.read";
export const TEMPLATE_CONTENT_PERMISSION_CREATE = "fair_crm.template_contents.create";
export const TEMPLATE_CONTENT_PERMISSION_UPDATE = "fair_crm.template_contents.update";
export const TEMPLATE_CONTENT_PERMISSION_DELETE = "fair_crm.template_contents.delete";

export function getGrantedTemplateContentPermissions(): Set<string> {
  if (config.devBypassEnabled) return new Set([TEMPLATE_CONTENT_PERMISSION_READ, TEMPLATE_CONTENT_PERMISSION_CREATE, TEMPLATE_CONTENT_PERMISSION_UPDATE, TEMPLATE_CONTENT_PERMISSION_DELETE]);
  const raw = import.meta.env.VITE_GRANTED_PERMISSIONS as string | undefined;
  if (!raw?.trim()) return new Set([TEMPLATE_CONTENT_PERMISSION_READ, TEMPLATE_CONTENT_PERMISSION_CREATE, TEMPLATE_CONTENT_PERMISSION_UPDATE, TEMPLATE_CONTENT_PERMISSION_DELETE]);
  return new Set(raw.split(",").map((item) => item.trim()).filter(Boolean));
}
