export interface CoreOrganizationSummary {
  id: string;
  status?: string;
}

/**
 * Resolve the effective organization for the authenticated Core user.
 *
 * Normal users receive only their directly-owned organization from Core.
 * Super Admins may receive multiple organizations; in that case keep the
 * preferred organization when it is valid, otherwise fall back to an active
 * organization returned by Core.
 */
export async function resolveSessionOrganizationId(
  coreBaseUrl: string,
  accessToken: string,
  preferredOrganizationId?: string | null,
): Promise<string> {
  const response = await fetch(`${coreBaseUrl}/api/v1/organizations`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Core organization lookup failed (${response.status})`);
  }

  const data = (await response.json()) as unknown;
  if (!Array.isArray(data)) {
    throw new Error("Core organization lookup returned an invalid payload");
  }

  const organizations = data.filter(
    (item): item is CoreOrganizationSummary =>
      typeof item === "object" &&
      item !== null &&
      "id" in item &&
      typeof (item as { id?: unknown }).id === "string",
  );

  if (organizations.length === 0) {
    throw new Error("Authenticated user has no organization");
  }

  const preferred = preferredOrganizationId?.trim();
  if (preferred && organizations.some((organization) => organization.id === preferred)) {
    return preferred;
  }

  const active = organizations.find((organization) => organization.status === "active");
  return active?.id ?? organizations[0].id;
}
