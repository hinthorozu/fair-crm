/** Standard paginated list API response (ADR-015). */

export type SortDirection = "asc" | "desc";

export interface ListPaginationInfo {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface ListSortingInfo {
  field: string;
  direction: SortDirection;
}

export interface StandardListResponse<T> {
  items: T[];
  pagination: ListPaginationInfo;
  sorting: ListSortingInfo;
  filters: Record<string, string | number | boolean | null | undefined>;
}

export interface ServerTablePagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface ServerTableSorting {
  field: string | null;
  direction: SortDirection | null;
}

export interface ServerTableState {
  search: string;
  filters: Record<string, string>;
  sorting: ServerTableSorting;
  pagination: ServerTablePagination;
}

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 25;
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

export type PageSizeOption = (typeof PAGE_SIZE_OPTIONS)[number];

/** @deprecated Use StandardListResponse pagination nested shape */
export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginationState {
  page: number;
  pageSize: number;
}
