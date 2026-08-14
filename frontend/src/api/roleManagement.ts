import { getAccessToken } from "../auth/session";
import { buildApiHeaders, config } from "../config";
import { formatPermissionDescription } from "../labels/permissionLabels";
import { ApiError, fetchWithTimeout } from "./client";

export interface RolePermission {
  id: string;
  code: string;
  description: string;
  lifecycle_state: "active" | "locked" | "inactive";
  is_assignable: boolean;
}

export interface ManagedRole {
  id: string;
  name: string;
  slug: string;
  role_kind: "protected_global" | "template" | "organization";
  organization_id: string | null;
  source_template_role_id: string | null;
  template_version: number;
  source_template_version: number | null;
  permissions_customized: boolean;
  is_assignable: boolean;
  is_protected: boolean;
  permission_ids: string[];
}

export interface TemplateSyncPreview {
  role_id: string;
  role_name: string;
  organization_id: string;
  current_version: number | null;
  target_version: number;
  add_count: number;
  remove_count: number;
}

async function request<T>(path: string, init: RequestInit = {}, organizationId?: string): Promise<T> {
  if (!getAccessToken() && !config.devBypassEnabled) throw new ApiError("Oturum bulunamadı.", 401);
  const headers = new Headers(buildApiHeaders(organizationId ? { "X-Organization-Id": organizationId } : {}));
  if (init.headers) new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  const response = await fetchWithTimeout(`${config.coreBaseUrl}/api/v1${path}`, { ...init, headers }, 15_000);
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!response.ok) {
    const message = typeof data === "object" && data !== null && "detail" in data
      ? String((data as { detail: unknown }).detail)
      : "İşlem tamamlanamadı.";
    throw new ApiError(message, response.status, data);
  }
  return data as T;
}

function localizePermissions(items: RolePermission[]): RolePermission[] {
  return items.map((permission) => ({
    ...permission,
    description: formatPermissionDescription(permission.code, permission.description),
  }));
}

export const listRoleTemplates = () => request<ManagedRole[]>("/role-templates");
export const listPlatformPermissions = async () => localizePermissions(await request<RolePermission[]>("/permissions"));
export const listManagedRoles = (organizationId: string) => request<ManagedRole[]>(`/organizations/${organizationId}/managed-roles`, {}, organizationId);
export const listRolePermissions = async (organizationId: string) => localizePermissions(await request<RolePermission[]>(`/organizations/${organizationId}/role-permissions`, {}, organizationId));
export const createOrganizationRole = (organizationId: string, payload: { name: string; slug: string; permission_ids: string[] }) => request<ManagedRole>(`/organizations/${organizationId}/roles`, { method: "POST", body: JSON.stringify(payload) }, organizationId);
export const updateOrganizationRole = (organizationId: string, roleId: string, payload: { name?: string; slug?: string }) => request<ManagedRole>(`/organizations/${organizationId}/roles/${roleId}`, { method: "PATCH", body: JSON.stringify(payload) }, organizationId);
export const updateOrganizationRolePermissions = (organizationId: string, roleId: string, permissionIds: string[]) => request<ManagedRole>(`/organizations/${organizationId}/roles/${roleId}/permissions`, { method: "PUT", body: JSON.stringify({ permission_ids: permissionIds }) }, organizationId);
export const deleteOrganizationRole = (organizationId: string, roleId: string) => request<null>(`/organizations/${organizationId}/roles/${roleId}`, { method: "DELETE" }, organizationId);
export const updateRoleTemplate = (roleId: string, permissionIds: string[]) => request<ManagedRole>(`/role-templates/${roleId}`, { method: "PATCH", body: JSON.stringify({ permission_ids: permissionIds }) });
export const deriveRoleTemplate = (roleId: string, payload: { organization_id: string; name: string; slug: string }) => request<ManagedRole>(`/role-templates/${roleId}/derive`, { method: "POST", body: JSON.stringify(payload) });
export const previewTemplateSync = (roleId: string, roleIds: string[]) => request<TemplateSyncPreview[]>(`/role-templates/${roleId}/sync/preview`, { method: "POST", body: JSON.stringify({ role_ids: roleIds }) });
export const syncRoleTemplate = (roleId: string, roleIds: string[]) => request<ManagedRole[]>(`/role-templates/${roleId}/sync`, { method: "POST", body: JSON.stringify({ role_ids: roleIds }) });
export const previewPermissionLifecycle = (permissionId: string, state: RolePermission["lifecycle_state"]) => request<{ affected_roles: number; affected_users: number }>(`/permissions/${permissionId}/lifecycle/preview`, { method: "POST", body: JSON.stringify({ state }) });
export const updatePermissionLifecycle = (permissionId: string, state: RolePermission["lifecycle_state"], reason?: string) => request<{ affected_roles: number; affected_users: number }>(`/permissions/${permissionId}/lifecycle`, { method: "POST", body: JSON.stringify({ state, reason: reason || null }) });
