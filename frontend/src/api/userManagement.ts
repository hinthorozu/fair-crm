import { getAccessToken } from "../auth/session";
import { buildApiHeaders, config } from "../config";
import { ApiError, fetchWithTimeout } from "./client";

export interface AssignableRole {
  id: string;
  name: string;
  slug: string;
}

export interface ManagedOrganization {
  id: string;
  name: string;
  slug: string;
}

export interface UserManagementContext {
  is_super_admin: boolean;
  organizations: ManagedOrganization[];
}

export interface ManagedUser {
  id: string;
  email: string;
  status: "active" | "inactive" | "suspended" | "locked" | string;
  organization_id: string;
  role: AssignableRole | null;
  created_at: string;
  updated_at: string;
  is_super_admin: boolean | null;
}

export interface ManagedUserList {
  items: ManagedUser[];
  can_manage_super_admin: boolean;
}

export interface ManualUserCreatePayload {
  email: string;
  password: string;
  role_id?: string;
  status: "active" | "inactive";
  is_super_admin?: boolean;
}

export interface ManualUserUpdatePayload {
  email?: string;
  password?: string;
  role_id?: string;
  status?: "active" | "inactive";
  is_super_admin?: boolean;
}

async function parseResponse(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function errorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}, organizationId?: string): Promise<T> {
  if (!getAccessToken() && !config.devBypassEnabled) {
    throw new ApiError("Oturum bulunamadı.", 401);
  }
  const headers = new Headers(
    buildApiHeaders(organizationId ? { "X-Organization-Id": organizationId } : {}),
  );
  if (init.headers) new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  const response = await fetchWithTimeout(
    `${config.coreBaseUrl}/api/v1${path}`,
    { ...init, headers },
    15_000,
  );
  const data = await parseResponse(response);
  if (!response.ok) {
    throw new ApiError(errorMessage(data, "İşlem tamamlanamadı."), response.status, data);
  }
  return data as T;
}

export function getUserManagementContext(): Promise<UserManagementContext> {
  return request<UserManagementContext>("/user-management/context");
}

export function listManagedUsers(organizationId: string): Promise<ManagedUserList> {
  return request<ManagedUserList>(
    `/organizations/${encodeURIComponent(organizationId)}/users`,
    {},
    organizationId,
  );
}

export function listAssignableRoles(organizationId: string): Promise<AssignableRole[]> {
  return request<AssignableRole[]>(
    `/organizations/${encodeURIComponent(organizationId)}/roles`,
    {},
    organizationId,
  );
}

export function createManagedUser(
  organizationId: string,
  payload: ManualUserCreatePayload,
): Promise<ManagedUser> {
  return request<ManagedUser>(
    `/organizations/${encodeURIComponent(organizationId)}/users/manual`,
    { method: "POST", body: JSON.stringify(payload) },
    organizationId,
  );
}

export function updateManagedUser(
  organizationId: string,
  userId: string,
  payload: ManualUserUpdatePayload,
): Promise<ManagedUser> {
  return request<ManagedUser>(
    `/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    organizationId,
  );
}

export async function deleteManagedUser(organizationId: string, userId: string): Promise<void> {
  await request<null>(
    `/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}`,
    { method: "DELETE" },
    organizationId,
  );
}
