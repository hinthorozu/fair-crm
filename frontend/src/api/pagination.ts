import type { PaginatedResponse } from "../types/pagination";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

function toPositiveInt(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) && n >= 1 ? Math.floor(n) : fallback;
}

function toNonNegativeInt(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
}

/** Normalize list API payloads (snake_case) into a stable paginated shape. */
export function normalizePaginatedResponse<T>(
  raw: unknown,
  defaults: { page?: number; page_size?: number } = {},
): PaginatedResponse<T> {
  const data = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const items = Array.isArray(data.items) ? (data.items as T[]) : [];

  const page = toPositiveInt(data.page, defaults.page ?? DEFAULT_PAGE);
  const page_size = toPositiveInt(data.page_size, defaults.page_size ?? DEFAULT_PAGE_SIZE);

  const totalFromApi = toNonNegativeInt(data.total);
  const total = totalFromApi ?? items.length;

  const totalPagesFromApi = toNonNegativeInt(data.total_pages);
  let total_pages = totalPagesFromApi;
  if (total_pages === null) {
    if (total === 0) {
      total_pages = 0;
    } else {
      total_pages = Math.max(1, Math.ceil(total / page_size));
    }
  }

  return { items, page, page_size, total, total_pages };
}
