import { buildApiHeaders, config } from "../config";
import { ApiError, fetchWithTimeout } from "./client";

export type OrganizationStatus = "active" | "suspended" | string;

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: OrganizationStatus;
  created_at: string;
  updated_at: string;
}

interface OrganizationListResponse {
  items: Organization[];
}

interface CreateOrganizationResponse {
  organization: Organization;
  membership_id: string;
}

export interface CreateOrganizationPayload {
  name: string;
  slug: string;
}

export interface UpdateOrganizationPayload {
  name: string;
}

export interface CreateOrganizationUserPayload {
  email: string;
  temporary_password: string;
  role_slug?: string;
}

export interface CreateOrganizationUserResponse {
  user_id: string;
  email: string;
  must_change_password: boolean;
  membership: {
    id: string;
    user_id: string;
    organization_id: string;
    status: string;
    joined_at: string | null;
  };
}

export interface InviteMemberResponse {
  invite_id: string;
  token: string;
  expires_at: string;
}

async function coreRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetchWithTimeout(`${config.coreBaseUrl}${path}`, {
    ...options,
    headers: buildApiHeaders(options.headers ?? {}),
  });

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") message = detail;
    }
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export async function listOrganizations(): Promise<Organization[]> {
  const response = await coreRequest<OrganizationListResponse>("/api/v1/admin/organizations");
  return response.items;
}

export async function createOrganization(
  payload: CreateOrganizationPayload,
): Promise<Organization> {
  const response = await coreRequest<CreateOrganizationResponse>("/api/v1/admin/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.organization;
}

export async function updateOrganization(
  organizationId: string,
  payload: UpdateOrganizationPayload,
): Promise<Organization> {
  return coreRequest<Organization>(`/api/v1/admin/organizations/${encodeURIComponent(organizationId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteOrganization(organizationId: string): Promise<void> {
  await coreRequest<null>(`/api/v1/admin/organizations/${encodeURIComponent(organizationId)}`, {
    method: "DELETE",
  });
}

function organizationScopedHeaders(organizationId: string): HeadersInit {
  return { "X-Organization-Id": organizationId };
}

export async function createOrganizationUser(
  organizationId: string,
  payload: CreateOrganizationUserPayload,
): Promise<CreateOrganizationUserResponse> {
  return coreRequest<CreateOrganizationUserResponse>(
    `/api/v1/organizations/${encodeURIComponent(organizationId)}/users`,
    {
      method: "POST",
      headers: organizationScopedHeaders(organizationId),
      body: JSON.stringify(payload),
    },
  );
}

export async function inviteOrganizationUser(
  organizationId: string,
  email: string,
): Promise<InviteMemberResponse> {
  return coreRequest<InviteMemberResponse>(
    `/api/v1/organizations/${encodeURIComponent(organizationId)}/memberships/invite`,
    {
      method: "POST",
      headers: organizationScopedHeaders(organizationId),
      body: JSON.stringify({ email }),
    },
  );
}
