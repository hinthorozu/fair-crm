interface CoreOrganizationSummary {
  id?: unknown;
  name?: unknown;
}

interface CoreUserManagementContext {
  is_super_admin?: unknown;
  organization_id?: unknown;
  organizations?: unknown;
}

export interface SessionIdentity {
  isSuperAdmin: boolean;
  organizationId: string | null;
  organizationName: string | null;
}

/**
 * Resolve the authenticated user's platform-level Super Admin flag from Core.
 *
 * This is identity context, not an inferred role or permission sentinel. Failure
 * is fail-closed and must be handled by the caller as `false`.
 */
export async function resolveSessionIdentity(
  coreBaseUrl: string,
  accessToken: string,
): Promise<SessionIdentity> {
  const response = await fetch(`${coreBaseUrl}/api/v1/user-management/context`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Core Super Admin lookup failed (${response.status})`);
  }

  const data = (await response.json()) as CoreUserManagementContext;
  if (typeof data.is_super_admin !== "boolean") {
    throw new Error("Core Super Admin lookup returned an invalid payload");
  }

  const organizationId = typeof data.organization_id === "string" && data.organization_id.trim()
    ? data.organization_id.trim()
    : null;
  const organizations = Array.isArray(data.organizations) ? data.organizations : [];
  const match = organizations.find(
    (item): item is CoreOrganizationSummary =>
      typeof item === "object" && item !== null && item.id === organizationId,
  );
  const organizationName = typeof match?.name === "string" && match.name.trim() ? match.name.trim() : null;

  return {
    isSuperAdmin: data.is_super_admin,
    organizationId,
    organizationName,
  };
}

export async function resolveSessionSuperAdmin(
  coreBaseUrl: string,
  accessToken: string,
): Promise<boolean> {
  const identity = await resolveSessionIdentity(coreBaseUrl, accessToken);
  return identity.isSuperAdmin;
}
