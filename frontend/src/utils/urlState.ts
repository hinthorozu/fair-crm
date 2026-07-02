/** URL query string helpers for server-side table state (ADR-015 / ADR-019). */

export function readSearchParams(search?: string): URLSearchParams {
  const raw = search ?? (typeof window !== "undefined" ? window.location.search : "");
  return new URLSearchParams(raw.startsWith("?") ? raw.slice(1) : raw);
}

export function buildLocationSearch(params: URLSearchParams): string {
  const value = params.toString();
  return value ? `?${value}` : "";
}

export function getTableStateFromUrl(
  keys: {
    page?: string;
    pageSize?: string;
    search?: string;
    sortBy?: string;
    sortOrder?: string;
    filterKeys?: string[];
  },
  search?: string,
): {
  page: number;
  pageSize: number;
  search: string;
  sortBy: string | null;
  sortOrder: "asc" | "desc" | null;
  filters: Record<string, string>;
} {
  const params = readSearchParams(search);
  const page = Math.max(1, Number(params.get(keys.page ?? "page") ?? 1) || 1);
  const pageSize = Math.max(1, Number(params.get(keys.pageSize ?? "pageSize") ?? 25) || 25);
  const searchValue = params.get(keys.search ?? "search") ?? "";
  const sortByKey = keys.sortBy ?? "sort_by";
  const sortOrderKey = keys.sortOrder ?? "sort_order";
  const sortBy =
    params.get(sortByKey) ??
    params.get("sort_by") ??
    params.get("sort");
  const sortOrderRaw =
    params.get(sortOrderKey) ??
    params.get("sort_order") ??
    params.get("direction") ??
    params.get("sort_dir");
  const sortOrder =
    sortOrderRaw === "asc" || sortOrderRaw === "desc" ? sortOrderRaw : null;
  const filters: Record<string, string> = {};
  for (const key of keys.filterKeys ?? []) {
    const value = params.get(key);
    if (value) filters[key] = value;
  }
  return { page, pageSize, search: searchValue, sortBy, sortOrder, filters };
}

export function writeTableStateToUrl(
  state: {
    page: number;
    pageSize: number;
    search: string;
    sortBy: string | null;
    sortOrder: "asc" | "desc" | null;
    filters: Record<string, string | undefined>;
  },
  keys: {
    page?: string;
    pageSize?: string;
    search?: string;
    sortBy?: string;
    sortOrder?: string;
    filterKeys?: string[];
  },
  baseParams?: URLSearchParams,
): string {
  const params = new URLSearchParams(baseParams?.toString() ?? "");

  const pageKey = keys.page ?? "page";
  const pageSizeKey = keys.pageSize ?? "pageSize";
  const searchKey = keys.search ?? "search";
  const sortByKey = keys.sortBy ?? "sort_by";
  const sortOrderKey = keys.sortOrder ?? "sort_order";

  if (state.page > 1) params.set(pageKey, String(state.page));
  else params.delete(pageKey);

  if (state.pageSize !== 25) params.set(pageSizeKey, String(state.pageSize));
  else params.delete(pageSizeKey);

  if (state.search.trim()) params.set(searchKey, state.search.trim());
  else params.delete(searchKey);

  if (state.sortBy) params.set(sortByKey, state.sortBy);
  else params.delete(sortByKey);

  if (state.sortOrder) params.set(sortOrderKey, state.sortOrder);
  else params.delete(sortOrderKey);

  // Remove legacy sort params when writing canonical state.
  params.delete("sort");
  params.delete("direction");
  params.delete("sort_dir");

  for (const key of keys.filterKeys ?? []) {
    const value = state.filters[key];
    if (value) params.set(key, value);
    else params.delete(key);
  }

  return buildLocationSearch(params);
}

export function navigateWithSearch(pathname: string, search: string) {
  const next = `${pathname}${search}`;
  const current = `${window.location.pathname}${window.location.search}`;
  if (current === next) {
    return;
  }
  window.history.pushState(null, "", next);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
