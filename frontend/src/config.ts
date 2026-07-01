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

const DEV_APP_ENVS = new Set(["development", "local", "test"]);

function resolveAppEnv(): string {
  return envString(import.meta.env.VITE_APP_ENV, import.meta.env.MODE).toLowerCase();
}

/**
 * Dev bypass is active when:
 * - Vite dev server / non-production build, AND
 * - VITE_APP_ENV (or Vite MODE) is development|local|test, OR
 * - VITE_DEV_BYPASS_ENABLED=true
 *
 * Production builds (`import.meta.env.PROD`) never enable bypass, regardless of env vars.
 */
function resolveDevBypassEnabled(): boolean {
  if (import.meta.env.PROD) {
    return false;
  }

  const appEnv = resolveAppEnv();
  if (DEV_APP_ENVS.has(appEnv)) {
    return true;
  }

  const explicit = import.meta.env.VITE_DEV_BYPASS_ENABLED;
  if (explicit !== undefined && explicit.trim() !== "") {
    return envBool(explicit, false);
  }

  return false;
}

export const config = {
  apiBaseUrl: envString(import.meta.env.VITE_API_BASE_URL, "http://127.0.0.1:8001"),
  appEnv: resolveAppEnv(),
  /** True only in non-production builds when dev bypass rules match. */
  devBypassEnabled: resolveDevBypassEnabled(),
  devBypassToken: envString(import.meta.env.VITE_DEV_BYPASS_TOKEN, "dev-bypass"),
  organizationId: envString(
    import.meta.env.VITE_ORGANIZATION_ID,
    "00000000-0000-4000-8000-000000000010",
  ),
};

/** Headers sent on every API request. Dev bypass headers are omitted in production builds. */
export function buildApiHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (config.devBypassEnabled) {
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
