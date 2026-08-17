import { refreshAccessToken } from "../api/auth";
import { config } from "../config";
import { fetchGrantedCorePermissions } from "../permissions/corePermissions";
import { resolveSessionOrganizationId } from "./organizationResolver";
import {
  clearSession,
  notifySessionExpired,
  readSession,
  saveSession,
  type AuthSession,
} from "./session";
import { resolveSessionSuperAdmin } from "./superAdminResolver";

let inflightRefresh: Promise<string | null> | null = null;

async function applyAccessToken(accessToken: string, expiresIn: number): Promise<void> {
  const current = readSession();
  let organizationId = current?.organizationId ?? config.organizationId;
  try {
    organizationId = await resolveSessionOrganizationId(
      config.coreBaseUrl,
      accessToken,
      organizationId,
    );
  } catch {
    // Keep the previous organization only as a fail-closed fallback.
  }

  let isSuperAdmin = false;
  try {
    isSuperAdmin = await resolveSessionSuperAdmin(config.coreBaseUrl, accessToken);
  } catch {
    isSuperAdmin = false;
  }

  let permissions: string[] = [];
  try {
    permissions = await fetchGrantedCorePermissions(
      config.coreBaseUrl,
      accessToken,
      organizationId,
    );
  } catch {
    permissions = [];
  }
  const next: AuthSession = {
    accessToken,
    organizationId,
    email: current?.email,
    permissions,
    isSuperAdmin,
    expiresIn,
  };
  saveSession(next);
}

export type RefreshOptions = {
  legacyRefreshToken?: string;
  /** When true, failure does not emit session-expired (used for boot probe). */
  silent?: boolean;
};

/**
 * Single-flight refresh: concurrent 401s share one refresh call.
 * Returns the new access token, or null if refresh failed.
 */
export async function refreshSessionSingleFlight(
  options: RefreshOptions = {},
): Promise<string | null> {
  if (inflightRefresh) {
    return inflightRefresh;
  }

  const { legacyRefreshToken, silent = false } = options;

  inflightRefresh = (async () => {
    try {
      const result = await refreshAccessToken(legacyRefreshToken);
      await applyAccessToken(result.access_token, result.expires_in);
      return result.access_token;
    } catch {
      clearSession();
      if (!silent) {
        notifySessionExpired();
      }
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();

  return inflightRefresh;
}

/** Test helper — reset single-flight state between tests. */
export function resetRefreshCoordinatorForTests(): void {
  inflightRefresh = null;
}
