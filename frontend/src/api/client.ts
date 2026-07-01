import { buildApiHeaders, config } from "../config";

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

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${config.apiBaseUrl}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: buildApiHeaders(options.headers ?? {}),
  });

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
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `HTTP ${response.status}`;
    throw new ApiError(detail, response.status, data);
  }

  return data as T;
}
