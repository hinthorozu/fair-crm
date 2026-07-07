import { buildApiHeaders, config } from "../config";
import { getAccessToken, clearSession, notifySessionExpired } from "../auth/session";

export const API_REQUEST_TIMEOUT_MS = 30_000;
/** Import analyze can process large batches against full CRM — allow longer than default list calls. */
export const ANALYZE_IMPORT_TIMEOUT_MS = 120_000;
/** Duplicate group listing may aggregate large completed analysis datasets. */
export const DUPLICATE_GROUPS_LIST_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const NOT_FOUND_DETAILS = new Set(["Not Found", "Customer not found"]);

export function formatApiErrorMessage(
  status: number,
  detail: string,
  fallback: string,
): string {
  if (status === 404 && NOT_FOUND_DETAILS.has(detail)) {
    return "Müşteri bulunamadı veya arşivden çıkarılamadı.";
  }
  return detail || fallback;
}

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException
    ? err.name === "AbortError"
    : err instanceof Error && err.name === "AbortError";
}

/** Fetch with timeout; used by apiRequest and multipart uploads. */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = API_REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  const externalSignal = options.signal;
  if (externalSignal) {
    if (externalSignal.aborted) {
      window.clearTimeout(timeoutId);
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err) {
    if (isAbortError(err)) {
      throw new ApiError(
        "Sunucu yanıt vermedi. Backend çalışıyor mu? (Zaman aşımı)",
        0,
      );
    }
    throw err;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = API_REQUEST_TIMEOUT_MS,
): Promise<T> {
  const url = `${config.apiBaseUrl}${path}`;
  const response = await fetchWithTimeout(
    url,
    {
      ...options,
      headers: buildApiHeaders(options.headers ?? {}),
    },
    timeoutMs,
  );

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
    if (response.status === 401 && getAccessToken()) {
      clearSession();
      notifySessionExpired();
    }
    let detail = `HTTP ${response.status}`;
    if (typeof data === "object" && data !== null) {
      if ("message" in data && data.message) {
        detail = String(data.message);
      } else if ("detail" in data && data.detail) {
        detail = String(data.detail);
      }
    }
    throw new ApiError(detail, response.status, data);
  }

  return data as T;
}
