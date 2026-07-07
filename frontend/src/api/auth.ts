import { fetchWithTimeout, ApiError } from "./client";
import { config } from "../config";
import { authLabels } from "../labels/authLabels";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
}

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

export async function loginWithCredentials(payload: LoginRequest): Promise<LoginResponse> {
  const url = `${config.coreBaseUrl}/api/v1/auth/login`;
  let response: Response;
  try {
    response = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(parseLoginError(response.status, data), response.status, data);
  }

  if (
    typeof data !== "object" ||
    data === null ||
    !("access_token" in data) ||
    typeof (data as LoginResponse).access_token !== "string"
  ) {
    throw new ApiError(authLabels.loginFailed, response.status, data);
  }

  return data as LoginResponse;
}

export async function logoutFromCore(refreshToken: string): Promise<void> {
  const url = `${config.coreBaseUrl}/api/v1/auth/logout`;
  try {
    const response = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      15_000,
    );
    if (!response.ok && response.status !== 204) {
      return;
    }
  } catch {
    // Best-effort: local session is cleared even if Core is unreachable.
  }
}
