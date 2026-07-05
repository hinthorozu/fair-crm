import { config } from "../config";

export const MAIL_TEMPLATE_PERMISSION_READ = "fair_crm.mail_templates.read";
export const MAIL_TEMPLATE_PERMISSION_CREATE = "fair_crm.mail_templates.create";
export const MAIL_TEMPLATE_PERMISSION_UPDATE = "fair_crm.mail_templates.update";
export const MAIL_TEMPLATE_PERMISSION_DELETE = "fair_crm.mail_templates.delete";
export const MAIL_TEMPLATE_PERMISSION_RENDER = "fair_crm.mail_templates.render";
export const MAIL_TEMPLATE_PERMISSION_TEST_SEND = "fair_crm.mail_templates.test_send";

export const MAIL_TEMPLATE_PERMISSIONS_ALL = [
  MAIL_TEMPLATE_PERMISSION_READ,
  MAIL_TEMPLATE_PERMISSION_CREATE,
  MAIL_TEMPLATE_PERMISSION_UPDATE,
  MAIL_TEMPLATE_PERMISSION_DELETE,
  MAIL_TEMPLATE_PERMISSION_RENDER,
  MAIL_TEMPLATE_PERMISSION_TEST_SEND,
] as const;

export type MailTemplatePermissionAction =
  | "read"
  | "create"
  | "update"
  | "delete"
  | "render"
  | "test_send";

const ACTION_TO_PERMISSION: Record<MailTemplatePermissionAction, string> = {
  read: MAIL_TEMPLATE_PERMISSION_READ,
  create: MAIL_TEMPLATE_PERMISSION_CREATE,
  update: MAIL_TEMPLATE_PERMISSION_UPDATE,
  delete: MAIL_TEMPLATE_PERMISSION_DELETE,
  render: MAIL_TEMPLATE_PERMISSION_RENDER,
  test_send: MAIL_TEMPLATE_PERMISSION_TEST_SEND,
};

function parseGrantedPermissions(raw: string | undefined): Set<string> | null {
  if (!raw?.trim()) {
    return null;
  }
  return new Set(
    raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
}

export function getGrantedMailTemplatePermissions(): Set<string> {
  if (config.devBypassEnabled) {
    return new Set(MAIL_TEMPLATE_PERMISSIONS_ALL);
  }
  const configured = parseGrantedPermissions(import.meta.env.VITE_GRANTED_PERMISSIONS);
  if (configured) {
    return configured;
  }
  return new Set(MAIL_TEMPLATE_PERMISSIONS_ALL);
}

export function hasMailTemplatePermission(
  grantedPermissions: Set<string>,
  permissionCode: string,
): boolean {
  return grantedPermissions.has(permissionCode);
}

export function canPerformMailTemplateAction(
  grantedPermissions: Set<string>,
  action: MailTemplatePermissionAction,
): boolean {
  return hasMailTemplatePermission(grantedPermissions, ACTION_TO_PERMISSION[action]);
}

export function canSetDefaultMailTemplate(
  template: { is_default: boolean; is_active: boolean },
  grantedPermissions: Set<string>,
): boolean {
  return (
    canPerformMailTemplateAction(grantedPermissions, "update") &&
    template.is_active &&
    !template.is_default
  );
}
