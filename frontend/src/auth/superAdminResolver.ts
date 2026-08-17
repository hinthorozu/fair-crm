interface CoreUserManagementContext {
  is_super_admin?: unknown;
}

/**
 * Resolve the authenticated user's platform-level Super Admin flag from Core.
 *
 * This is identity context, not an inferred role or permission sentinel. Failure
 * is fail-closed and must be handled by the caller as `false`.
 */
export async function resolveSessionSuperAdmin(
  coreBaseUrl: string,
  accessToken: string,
): Promise<boolean> {
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

  return data.is_super_admin;
}
