import React from "react";
import { DataTable } from "./DataTable";
import { ServerDataTableFrame } from "./ServerDataTableFrame";
import type { ServerDataTableController } from "../../hooks/useServerDataTable";
import type { SortDirection } from "../../types/listTable";

/** Column definition for Universal Server-Side DataTable (ADR-019). */
export interface UniversalDataTableColumn<T> {
  key: string;
  title: React.ReactNode;
  /** Data columns default to sortable; set false for Actions. */
  sortable?: boolean;
  /** API whitelist field; defaults to `key`. */
  sortField?: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

interface UniversalDataTableBaseProps<T> {
  columns: UniversalDataTableColumn<T>[];
  rowKey: (row: T) => string;
  emptyState?: React.ReactNode;
  className?: string;
}

interface UniversalDataTableStandaloneProps<T> extends UniversalDataTableBaseProps<T> {
  items: T[];
  sorting?: { field: string | null; direction: SortDirection | null };
  onSortChange?: (field: string) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  table?: never;
  toolbar?: never;
  skeletonCols?: never;
}

interface UniversalDataTableServerProps<T> extends UniversalDataTableBaseProps<T> {
  table: ServerDataTableController<T>;
  toolbar?: React.ReactNode;
  skeletonCols?: number;
  items?: never;
  sorting?: never;
  onSortChange?: never;
  loading?: never;
  error?: never;
  onRetry?: never;
}

export type UniversalDataTableProps<T> =
  | UniversalDataTableStandaloneProps<T>
  | UniversalDataTableServerProps<T>;

function mapColumns<T>(columns: UniversalDataTableColumn<T>[]) {
  return columns.map((column) => ({
    id: column.key,
    header: column.title,
    sortable: column.sortable !== false,
    sortField: column.sortField ?? column.key,
    render: column.render,
    className: column.className,
    dataLabel: typeof column.title === "string" ? column.title : undefined,
  }));
}

/**
 * Universal Server-Side DataTable — sortable data columns via column config.
 * Set `sortable: false` only on Actions columns.
 */
export function UniversalDataTable<T>(props: UniversalDataTableProps<T>) {
  const { columns, rowKey, emptyState, className } = props;

  if ("table" in props && props.table) {
    const { table, toolbar, skeletonCols } = props;
    const dataColumns = columns.filter((column) => column.sortable !== false).length;
    const showEmpty = !table.loading && !table.error && table.items.length === 0;

    return (
      <ServerDataTableFrame
        table={table}
        toolbar={toolbar}
        skeletonCols={skeletonCols ?? Math.max(dataColumns + 1, 4)}
      >
        {showEmpty && emptyState ? (
          emptyState
        ) : (
          <DataTable
            columns={mapColumns(columns)}
            data={table.items}
            rowKey={rowKey}
            sorting={table.sorting}
            onSortChange={table.setSort}
            className={className}
          />
        )}
      </ServerDataTableFrame>
    );
  }

  const { items, sorting, onSortChange, loading, error, onRetry } = props;
  if (!loading && items.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <DataTable
      columns={mapColumns(columns)}
      data={items}
      rowKey={rowKey}
      sorting={
        sorting?.field && sorting.direction
          ? { field: sorting.field, direction: sorting.direction }
          : sorting?.field
            ? { field: sorting.field, direction: sorting.direction ?? "asc" }
            : null
      }
      loading={loading}
      error={error}
      onSortChange={onSortChange}
      onRetry={onRetry}
      emptyState={emptyState}
      className={className}
    />
  );
}
