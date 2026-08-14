import { refreshAccessToken } from "../api/auth";
import { config } from "../config";
import { fetchGrantedCorePermissions } from "../permissions/corePermissions";
import {
  clearSession,
  notifySessionExpired,
  readSession,
  saveSession,
  type AuthSession,
} from "./session";

let inflightRefresh: Promise<string | null> | null = null;

async function applyAccessToken(accessToken: string, expiresIn: number): Promise<void> {
  const current = readSession();
  const organizationId = current?.organizationId ?? config.organizationId;
  const permissions = await fetchGrantedCorePermissions(
    config.coreBaseUrl,
    accessToken,
    organizationId,
  );
  const next: AuthSession = {
    accessToken,
    organizationId,
    email: current?.email,
    permissions,
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
