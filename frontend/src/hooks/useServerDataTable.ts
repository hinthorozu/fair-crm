import React from "react";
import type { StandardListResponse, SortDirection } from "../types/listTable";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/listTable";
import {
  getTableStateFromUrl,
  navigateWithSearch,
  readSearchParams,
  writeTableStateToUrl,
} from "../utils/urlState";

export interface ServerTableFetchParams {
  page: number;
  pageSize: number;
  search: string;
  sortBy: string | null;
  sortOrder: SortDirection | null;
  filters: Record<string, string>;
}

export interface ServerTableRefreshOverrides {
  filters?: Record<string, string>;
  page?: number;
  /**
   * When true, keep existing rows on screen (no skeleton / loading flip).
   * Failures leave current data untouched and do not surface a new error banner.
   * Default callers are unchanged: omit or pass false for a normal loading fetch.
   */
  silent?: boolean;
}

export interface UseServerDataTableOptions<T> {
  fetchFn: (params: ServerTableFetchParams) => Promise<StandardListResponse<T>>;
  defaultSort?: { field: string; direction: SortDirection };
  defaultFilters?: Record<string, string>;
  pageSize?: number;
  filterKeys?: string[];
  urlSync?: boolean;
  urlPath?: string;
  debounceMs?: number;
  enabled?: boolean;
}

function nextSortCycle(
  field: string,
  current: { field: string | null; direction: SortDirection | null },
  defaultSort?: { field: string; direction: SortDirection },
): { field: string | null; direction: SortDirection | null } {
  if (current.field !== field) {
    return { field, direction: "asc" };
  }
  if (current.direction === "asc") {
    return { field, direction: "desc" };
  }
  if (defaultSort && field === defaultSort.field) {
    return { field: null, direction: null };
  }
  return { field: null, direction: null };
}

export function useServerDataTable<T>({
  fetchFn,
  defaultSort,
  defaultFilters = {},
  pageSize: initialPageSize = DEFAULT_PAGE_SIZE,
  filterKeys = [],
  urlSync = false,
  urlPath,
  debounceMs = 300,
  enabled = true,
}: UseServerDataTableOptions<T>) {
  const fetchRef = React.useRef(fetchFn);
  React.useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  const urlState = React.useMemo(
    () =>
      urlSync
        ? getTableStateFromUrl({ filterKeys })
        : {
            page: DEFAULT_PAGE,
            pageSize: initialPageSize,
            search: "",
            sortBy: defaultSort?.field ?? null,
            sortOrder: defaultSort?.direction ?? null,
            filters: { ...defaultFilters },
          },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const [items, setItems] = React.useState<T[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const requestIdRef = React.useRef(0);
  const [search, setSearchState] = React.useState(urlState.search);
  const [debouncedSearch, setDebouncedSearch] = React.useState(urlState.search);
  const [page, setPageState] = React.useState(urlState.page);
  const [pageSize, setPageSizeState] = React.useState(urlState.pageSize || initialPageSize);
  const [sorting, setSorting] = React.useState<{
    field: string | null;
    direction: SortDirection | null;
  }>({
    field: urlState.sortBy ?? defaultSort?.field ?? null,
    direction: urlState.sortOrder ?? defaultSort?.direction ?? null,
  });
  const [filters, setFiltersState] = React.useState<Record<string, string>>({
    ...defaultFilters,
    ...urlState.filters,
  });
  const [pagination, setPagination] = React.useState({
    page: DEFAULT_PAGE,
    pageSize: initialPageSize,
    totalItems: 0,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
  });
  const [responseSorting, setResponseSorting] = React.useState(
    defaultSort ?? { field: "", direction: "asc" as SortDirection },
  );
  const [responseFilters, setResponseFilters] = React.useState<Record<string, unknown>>({});
  const [filterCounts, setFilterCounts] = React.useState<Record<string, number> | null>(null);

  const syncUrl = React.useCallback(
    (next: {
      page: number;
      pageSize: number;
      search: string;
      sortBy: string | null;
      sortOrder: SortDirection | null;
      filters: Record<string, string>;
    }) => {
      if (!urlSync) return;
      const pathname = urlPath ?? window.location.pathname;
      const base = readSearchParams();
      for (const key of filterKeys) base.delete(key);
      base.delete("page");
      base.delete("pageSize");
      base.delete("search");
      base.delete("sort_by");
      base.delete("sort_order");
      base.delete("sort");
      base.delete("direction");
      const searchStr = writeTableStateToUrl(next, { filterKeys }, base);
      navigateWithSearch(pathname, searchStr);
    },
    [filterKeys, urlPath, urlSync],
  );

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), debounceMs);
    return () => clearTimeout(timer);
  }, [search, debounceMs]);

  const defaultSortField = defaultSort?.field;
  const defaultSortDirection = defaultSort?.direction;

  const load = React.useCallback(async (overrides?: ServerTableRefreshOverrides) => {
    if (!enabled) {
      setLoading(false);
      setIsRefreshing(false);
      return;
    }
    const silent = Boolean(overrides?.silent);
    const requestId = ++requestIdRef.current;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
      setIsRefreshing(false);
      setError(null);
    }
    try {
      const effectiveSortBy = sorting.field ?? defaultSortField ?? null;
      const effectiveSortOrder =
        sorting.direction ??
        (sorting.field ? defaultSortDirection : null) ??
        defaultSortDirection ??
        null;
      const effectiveFilters = overrides?.filters ?? filters;
      const effectivePage = overrides?.page ?? page;

      const res = await fetchRef.current({
        page: effectivePage,
        pageSize,
        search: debouncedSearch,
        sortBy: effectiveSortBy,
        sortOrder: effectiveSortOrder,
        filters: effectiveFilters,
      });
      if (requestId !== requestIdRef.current) return;
      setItems(res.items);
      setPagination(res.pagination);
      setResponseSorting(res.sorting);
      setResponseFilters(res.filters);
      setFilterCounts(res.counts ?? null);
      if (silent) setError(null);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      if (!silent) {
        setError(err instanceof Error ? err.message : "Liste yüklenemedi.");
      }
    } finally {
      if (requestId === requestIdRef.current) {
        if (silent) {
          setIsRefreshing(false);
        } else {
          setLoading(false);
        }
      }
    }
  }, [
    debouncedSearch,
    defaultSortDirection,
    defaultSortField,
    enabled,
    filters,
    page,
    pageSize,
    sorting.direction,
    sorting.field,
  ]);

  React.useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    void load();
  }, [enabled, load]);

  React.useEffect(() => {
    if (!enabled || Object.keys(defaultFilters).length === 0) return;
    setFiltersState((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const [key, value] of Object.entries(defaultFilters)) {
        if (value && !prev[key]) {
          next[key] = value;
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [defaultFilters, enabled]);

  React.useEffect(() => {
    if (!urlSync) return;
    const onPopState = () => {
      const state = getTableStateFromUrl({ filterKeys });
      setSearchState((prev) => (prev === state.search ? prev : state.search));
      setDebouncedSearch((prev) => (prev === state.search ? prev : state.search));
      setPageState((prev) => (prev === state.page ? prev : state.page));
      setPageSizeState((prev) => (prev === state.pageSize ? prev : state.pageSize));
      setSorting((prev) =>
        prev.field === state.sortBy && prev.direction === state.sortOrder
          ? prev
          : { field: state.sortBy, direction: state.sortOrder },
      );
      setFiltersState((prev) => {
        const next = { ...prev, ...state.filters };
        const keys = new Set([...Object.keys(prev), ...Object.keys(next), ...filterKeys]);
        for (const key of keys) {
          if ((prev[key] ?? "") !== (next[key] ?? "")) {
            return next;
          }
        }
        return prev;
      });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [filterKeys, urlSync]);

  const applyState = React.useCallback(
    (
      patch: Partial<{
        page: number;
        pageSize: number;
        search: string;
        sortBy: string | null;
        sortOrder: SortDirection | null;
        filters: Record<string, string>;
      }>,
    ) => {
      const next = {
        page: patch.page ?? page,
        pageSize: patch.pageSize ?? pageSize,
        search: patch.search ?? search,
        sortBy: patch.sortBy !== undefined ? patch.sortBy : sorting.field,
        sortOrder: patch.sortOrder !== undefined ? patch.sortOrder : sorting.direction,
        filters: patch.filters ?? filters,
      };
      if (patch.page !== undefined) setPageState(patch.page);
      if (patch.pageSize !== undefined) setPageSizeState(patch.pageSize);
      if (patch.search !== undefined) setSearchState(patch.search);
      if (patch.sortBy !== undefined || patch.sortOrder !== undefined) {
        setSorting({ field: next.sortBy, direction: next.sortOrder });
      }
      if (patch.filters !== undefined) setFiltersState(patch.filters);
      syncUrl(next);
    },
    [filters, page, pageSize, search, sorting.direction, sorting.field, syncUrl],
  );

  const effectiveSorting = {
    field: sorting.field ?? responseSorting.field ?? defaultSort?.field ?? "",
    direction:
      sorting.direction ?? responseSorting.direction ?? defaultSort?.direction ?? "asc",
  };

  return {
    items,
    loading,
    isRefreshing,
    error,
    search,
    filters,
    filterCounts,
    sorting: effectiveSorting,
    responseFilters,
    pagination,
    setSearch: (value: string) => applyState({ search: value, page: DEFAULT_PAGE }),
    setFilters: (next: Record<string, string>) =>
      applyState({ filters: next, page: DEFAULT_PAGE }),
    setFilter: (key: string, value: string) =>
      applyState({ filters: { ...filters, [key]: value }, page: DEFAULT_PAGE }),
    setSort: (field: string) => {
      const cycled = nextSortCycle(field, sorting, defaultSort);
      applyState({ sortBy: cycled.field, sortOrder: cycled.direction, page: DEFAULT_PAGE });
    },
    setSorting: (field: string | null, direction: SortDirection | null) =>
      applyState({ sortBy: field, sortOrder: direction, page: DEFAULT_PAGE }),
    setPage: (value: number) => applyState({ page: value }),
    setPageSize: (value: number) => applyState({ pageSize: value, page: DEFAULT_PAGE }),
    refresh: load,
    isEmpty: !loading && !error && items.length === 0,
    hasActiveFilters:
      Boolean(debouncedSearch.trim()) ||
      Object.values(filters).some((value) => Boolean(value)),
  };
}

export type ServerDataTableController<T> = ReturnType<typeof useServerDataTable<T>>;
