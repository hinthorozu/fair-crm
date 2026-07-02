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
  const [error, setError] = React.useState<string | null>(null);
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

  const load = React.useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const effectiveSortBy = sorting.field ?? defaultSortField ?? null;
      const effectiveSortOrder =
        sorting.direction ??
        (sorting.field ? defaultSortDirection : null) ??
        defaultSortDirection ??
        null;

      const res = await fetchRef.current({
        page,
        pageSize,
        search: debouncedSearch,
        sortBy: effectiveSortBy,
        sortOrder: effectiveSortOrder,
        filters,
      });
      setItems(res.items);
      setPagination(res.pagination);
      setResponseSorting(res.sorting);
      setResponseFilters(res.filters);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Liste yüklenemedi.");
    } finally {
      setLoading(false);
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
    void load();
  }, [load]);

  React.useEffect(() => {
    if (!urlSync) return;
    const onPopState = () => {
      const state = getTableStateFromUrl({ filterKeys });
      setSearchState(state.search);
      setDebouncedSearch(state.search);
      setPageState(state.page);
      setPageSizeState(state.pageSize);
      setSorting({ field: state.sortBy, direction: state.sortOrder });
      setFiltersState((prev) => ({ ...prev, ...state.filters }));
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
    error,
    search,
    filters,
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
