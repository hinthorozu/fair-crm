import { getGrantedCorePermissions } from "./corePermissions";

export const TEMPLATE_CONTENT_PERMISSION_READ = "fair_crm.template_contents.read";
export const TEMPLATE_CONTENT_PERMISSION_CREATE = "fair_crm.template_contents.create";
export const TEMPLATE_CONTENT_PERMISSION_UPDATE = "fair_crm.template_contents.update";
export const TEMPLATE_CONTENT_PERMISSION_DELETE = "fair_crm.template_contents.delete";

export function getGrantedTemplateContentPermissions(): Set<string> {
  return getGrantedCorePermissions();
}
