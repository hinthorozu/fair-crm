import { getAccessToken, getOrganizationId } from "./auth/session";

function envString(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

function envBool(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  const normalized = value.trim().toLowerCase();
  if (normalized === "true" || normalized === "1" || normalized === "yes") return true;
  if (normalized === "false" || normalized === "0" || normalized === "no") return false;
  return fallback;
}

function envInt(value: string | undefined, fallback: number): number {
  if (value === undefined) return fallback;
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function resolveAppEnv(): string {
  return envString(import.meta.env.VITE_APP_ENV, import.meta.env.MODE).toLowerCase();
}

/** Dev bypass is active only when VITE_DEV_BYPASS_ENABLED=true. */
function resolveDevBypassEnabled(): boolean {
  return envBool(import.meta.env.VITE_DEV_BYPASS_ENABLED, false);
}

/** Empty/unset VITE_CORE_BASE_URL → same-origin `/kyrox-core` (Vite/Nginx proxy). */
function resolveCoreBaseUrl(): string {
  return envString(import.meta.env.VITE_CORE_BASE_URL, "/kyrox-core");
}

/** Must match backend/Core ACCESS_TOKEN_EXPIRE_DAYS (default 15). */
export const ACCESS_TOKEN_EXPIRE_DAYS = envInt(import.meta.env.VITE_ACCESS_TOKEN_EXPIRE_DAYS, 15);
/** Must match backend/Core REFRESH_TOKEN_EXPIRE_DAYS (default 15). */
export const REFRESH_TOKEN_EXPIRE_DAYS = envInt(import.meta.env.VITE_REFRESH_TOKEN_EXPIRE_DAYS, 15);
export const ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60;

export const config = {
  /** Empty = same-origin relative `/api/v1/...` (Vite/Nginx proxy to backend). */
  apiBaseUrl: envString(import.meta.env.VITE_API_BASE_URL, ""),
  coreBaseUrl: resolveCoreBaseUrl(),
  appEnv: resolveAppEnv(),
  /** True only when VITE_DEV_BYPASS_ENABLED=true. Controls API bypass headers and login skip. */
  devBypassEnabled: resolveDevBypassEnabled(),
  devBypassToken: envString(import.meta.env.VITE_DEV_BYPASS_TOKEN, "dev-bypass"),
  organizationId: envString(
    import.meta.env.VITE_ORGANIZATION_ID,
    "00000000-0000-4000-8000-000000000010",
  ),
  accessTokenExpireDays: ACCESS_TOKEN_EXPIRE_DAYS,
  refreshTokenExpireDays: REFRESH_TOKEN_EXPIRE_DAYS,
  accessTokenExpireSeconds: ACCESS_TOKEN_EXPIRE_SECONDS,
};

/** Headers sent on every API request. Session JWT takes priority over dev bypass. */
export function buildApiHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const accessToken = getAccessToken();
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
    headers["X-Organization-Id"] = getOrganizationId() ?? config.organizationId;
  } else if (config.devBypassEnabled) {
    headers.Authorization = `Bearer ${config.devBypassToken}`;
    headers["X-Organization-Id"] = config.organizationId;
  }

  if (extra instanceof Headers) {
    extra.forEach((value, key) => {
      headers[key] = value;
    });
  } else if (Array.isArray(extra)) {
    for (const [key, value] of extra) {
      headers[key] = value;
    }
  } else {
    Object.assign(headers, extra);
  }

  return headers;
}
