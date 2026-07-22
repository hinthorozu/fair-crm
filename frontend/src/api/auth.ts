import { fetchWithTimeout, ApiError } from "./client";
import { ACCESS_TOKEN_EXPIRE_SECONDS, config } from "../config";
import { authLabels } from "../labels/authLabels";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type?: string;
  expires_in: number;
}

const CSRF_HEADER = { "X-Fair-CRM-Requested-With": "XMLHttpRequest" };

function parseLoginError(status: number, data: unknown): string {
  if (status === 401) {
    return authLabels.invalidCredentials;
  }
  if (status === 422) {
    return authLabels.invalidInput;
  }
  if (status === 0) {
    return authLabels.networkError;
  }

  if (typeof data === "object" && data !== null) {
    if ("detail" in data && data.detail) {
      const detail = data.detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: string };
        if (first?.msg) return first.msg;
      }
    }
    if ("message" in data && data.message) {
      return String(data.message);
    }
  }

  return authLabels.loginFailed;
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function assertAccessTokenResponse(data: unknown, status: number): AccessTokenResponse {
  if (
    typeof data !== "object" ||
    data === null ||
    !("access_token" in data) ||
    typeof (data as AccessTokenResponse).access_token !== "string"
  ) {
    throw new ApiError(authLabels.loginFailed, status, data);
  }
  const typed = data as AccessTokenResponse;
  const expiresIn =
    typeof typed.expires_in === "number" && typed.expires_in > 0
      ? typed.expires_in
      : ACCESS_TOKEN_EXPIRE_SECONDS;
  return {
    access_token: typed.access_token,
    token_type: typed.token_type,
    expires_in: expiresIn,
  };
}

/** Login via Fair CRM auth bridge (sets HttpOnly refresh cookie). */
export async function loginWithCredentials(payload: LoginRequest): Promise<AccessTokenResponse> {
  const url = `${config.apiBaseUrl}/api/v1/auth/login`;
  let response: Response;
  try {
    response = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...CSRF_HEADER },
        credentials: "include",
        body: JSON.stringify(payload),
      },
      30_000,
    );
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(authLabels.networkError, 0);
  }

  const data = await parseJson(response);
  if (!response.ok) {
    throw new ApiError(parseLoginError(response.status, data), response.status, data);
  }
  return assertAccessTokenResponse(data, response.status);
}

/**
 * Refresh access token using HttpOnly cookie (preferred) or legacy body token once.
 * Single-flight coordination lives in auth/refreshCoordinator.ts.
 */
export async function refreshAccessToken(legacyRefreshToken?: string): Promise<AccessTokenResponse> {
  const url = `${config.apiBaseUrl}/api/v1/auth/refresh`;
  const body =
    legacyRefreshToken && legacyRefreshToken.trim()
      ? JSON.stringify({ refresh_token: legacyRefreshToken.trim() })
      : "{}";

  let response: Response;
  try {
    response = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...CSRF_HEADER },
        credentials: "include",
        body,
      },
      15_000,
    );
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(authLabels.networkError, 0);
  }

  const data = await parseJson(response);
  if (!response.ok) {
    throw new ApiError(
      typeof data === "object" && data && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : "Oturum yenilenemedi",
      response.status,
      data,
    );
  }
  return assertAccessTokenResponse(data, response.status);
}

export async function logoutSession(legacyRefreshToken?: string): Promise<void> {
  const url = `${config.apiBaseUrl}/api/v1/auth/logout`;
  const body =
    legacyRefreshToken && legacyRefreshToken.trim()
      ? JSON.stringify({ refresh_token: legacyRefreshToken.trim() })
      : "{}";
  try {
    await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...CSRF_HEADER },
        credentials: "include",
        body,
      },
      15_000,
    );
  } catch {
    // Best-effort: local session is cleared even if backend is unreachable.
  }
}
