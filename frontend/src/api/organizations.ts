import { getAccessToken } from "../auth/session";
import { buildApiHeaders, config } from "../config";
import { ApiError, fetchWithTimeout } from "./client";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface CreateOrganizationResponse {
  organization: Organization;
  membership_id: string;
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

async function coreRequest<T>(
  path: string,
  init: RequestInit = {},
  organizationId?: string,
): Promise<T> {
  if (!getAccessToken() && !config.devBypassEnabled) {
    throw new ApiError("Oturum bulunamadı.", 401);
  }

  const headers = new Headers(
    buildApiHeaders(organizationId ? { "X-Organization-Id": organizationId } : {}),
  );
  if (init.headers) {
    new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  }

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

export async function listOrganizations(): Promise<Organization[]> {
  return coreRequest<Organization[]>("/organizations");
}

export async function createOrganization(name: string): Promise<Organization> {
  const response = await coreRequest<CreateOrganizationResponse>("/organizations", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  return response.organization;
}

export async function updateOrganization(id: string, name: string): Promise<Organization> {
  return coreRequest<Organization>(
    `/organizations/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify({ name }) },
    id,
  );
}

export async function deleteOrganization(id: string): Promise<void> {
  await coreRequest<null>(
    `/organizations/${encodeURIComponent(id)}`,
    { method: "DELETE" },
    id,
  );
}
