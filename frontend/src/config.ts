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

function resolveAppEnv(): string {
  return envString(import.meta.env.VITE_APP_ENV, import.meta.env.MODE).toLowerCase();
}

/** Dev bypass is active only when VITE_DEV_BYPASS_ENABLED=true. */
function resolveDevBypassEnabled(): boolean {
  return envBool(import.meta.env.VITE_DEV_BYPASS_ENABLED, false);
}

function resolveCoreBaseUrl(): string {
  const configured = import.meta.env.VITE_CORE_BASE_URL?.trim();
  if (configured) return configured;
  if (import.meta.env.DEV) {
    return "http://127.0.0.1:5173/kyrox-core";
  }
  return "http://127.0.0.1:8000";
}

export const config = {
  apiBaseUrl: envString(import.meta.env.VITE_API_BASE_URL, "http://127.0.0.1:8001"),
  coreBaseUrl: resolveCoreBaseUrl(),
  appEnv: resolveAppEnv(),
  /** True only when VITE_DEV_BYPASS_ENABLED=true. Controls API bypass headers and login skip. */
  devBypassEnabled: resolveDevBypassEnabled(),
  devBypassToken: envString(import.meta.env.VITE_DEV_BYPASS_TOKEN, "dev-bypass"),
  organizationId: envString(
    import.meta.env.VITE_ORGANIZATION_ID,
    "00000000-0000-4000-8000-000000000010",
  ),
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
