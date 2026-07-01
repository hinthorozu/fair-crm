import type {
  ListPaginationInfo,
  ListSortingInfo,
  StandardListResponse,
  SortDirection,
} from "../types/listTable";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/listTable";

function toPositiveInt(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) && n >= 1 ? Math.floor(n) : fallback;
}

function toNonNegativeInt(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
}

function readPagination(raw: Record<string, unknown>): ListPaginationInfo | null {
  const nested = raw.pagination;
  if (nested && typeof nested === "object") {
    const p = nested as Record<string, unknown>;
    const page = toPositiveInt(p.page, DEFAULT_PAGE);
    const pageSize = toPositiveInt(p.pageSize ?? p.page_size, DEFAULT_PAGE_SIZE);
    const totalItems = toNonNegativeInt(p.totalItems ?? p.total) ?? 0;
    let totalPages = toNonNegativeInt(p.totalPages ?? p.total_pages);
    if (totalPages === null) {
      totalPages = totalItems === 0 ? 0 : Math.max(1, Math.ceil(totalItems / pageSize));
    }
    return {
      page,
      pageSize,
      totalItems,
      totalPages,
      hasNext: Boolean(p.hasNext ?? (totalPages > 0 && page < totalPages)),
      hasPrevious: Boolean(p.hasPrevious ?? page > 1),
    };
  }
  return null;
}

function readSorting(raw: Record<string, unknown>): ListSortingInfo {
  const nested = raw.sorting;
  if (nested && typeof nested === "object") {
    const s = nested as Record<string, unknown>;
    const direction = s.direction === "asc" ? "asc" : "desc";
    return {
      field: typeof s.field === "string" ? s.field : "",
      direction,
    };
  }
  return { field: "", direction: "asc" };
}

/** Normalize list API payloads into StandardListResponse shape. */
export function normalizeStandardListResponse<T>(raw: unknown): StandardListResponse<T> {
  const data = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const items = Array.isArray(data.items) ? (data.items as T[]) : [];

  const pagination =
    readPagination(data) ??
    (() => {
      const page = toPositiveInt(data.page, DEFAULT_PAGE);
      const pageSize = toPositiveInt(data.page_size, DEFAULT_PAGE_SIZE);
      const totalItems = toNonNegativeInt(data.total) ?? items.length;
      let totalPages = toNonNegativeInt(data.total_pages);
      if (totalPages === null) {
        totalPages = totalItems === 0 ? 0 : Math.max(1, Math.ceil(totalItems / pageSize));
      }
      return {
        page,
        pageSize,
        totalItems,
        totalPages,
        hasNext: totalPages > 0 && page < totalPages,
        hasPrevious: page > 1,
      };
    })();

  const sorting = readSorting(data);
  const filters =
    data.filters && typeof data.filters === "object"
      ? (data.filters as Record<string, string | number | boolean | null | undefined>)
      : {};

  return { items, pagination, sorting, filters };
}

export function buildListQueryParams(state: {
  page?: number;
  pageSize?: number;
  search?: string;
  sort?: string | null;
  direction?: SortDirection | null;
  filters?: Record<string, string | undefined>;
}): URLSearchParams {
  const params = new URLSearchParams();
  if (state.page) params.set("page", String(state.page));
  if (state.pageSize) params.set("pageSize", String(state.pageSize));
  if (state.search?.trim()) params.set("search", state.search.trim());
  if (state.sort) params.set("sort", state.sort);
  if (state.direction) params.set("direction", state.direction);
  if (state.filters) {
    for (const [key, value] of Object.entries(state.filters)) {
      if (value !== undefined && value !== "") params.set(key, value);
    }
  }
  return params;
}
