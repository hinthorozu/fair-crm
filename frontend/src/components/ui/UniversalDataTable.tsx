import React from "react";
import { ResponsiveDataTable, type ColumnPriority } from "./ResponsiveDataTable";
import { ServerDataTableFrame } from "./ServerDataTableFrame";
import type { ServerDataTableRowSelectionController } from "../../hooks/useServerDataTableRowSelection";
import type { ServerDataTableController } from "../../hooks/useServerDataTable";
import type { SortDirection } from "../../types/listTable";
import { buildUniversalDataTableSelectionColumn } from "./UniversalDataTableSelection";

/** Column definition for Universal Server-Side DataTable (ADR-019 / ADR-032). */
export interface UniversalDataTableColumn<T> {
  key: string;
  title: React.ReactNode;
  /** Data columns default to sortable; set false for Actions. */
  sortable?: boolean;
  /** API whitelist field; defaults to `key`. */
  sortField?: string;
  render: (row: T) => React.ReactNode;
  className?: string;
  /** Responsive stacked-row label; defaults to `title` when it is a string. */
  dataLabel?: string;
  /**
   * primary — main row always
   * secondary — desktop main; tablet/mobile expand
   * technical — expand / technical panel only (never main table)
   */
  priority?: ColumnPriority;
}

export interface UniversalDataTableRowSelectionConfig<T> {
  controller: ServerDataTableRowSelectionController;
  title: string;
  selectAllAriaLabel: string;
  rowAriaLabel: (row: T) => string;
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
  showPagination?: boolean;
  /** Optional row selection (ADR-029); prepends a Selection column. */
  rowSelection?: UniversalDataTableRowSelectionConfig<T>;
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
    dataLabel:
      column.dataLabel ?? (typeof column.title === "string" ? column.title : undefined),
    priority: column.priority ?? "primary",
  }));
}

function withSelectionColumn<T extends { id: string }>(
  columns: UniversalDataTableColumn<T>[],
  rowSelection: UniversalDataTableRowSelectionConfig<T> | undefined,
): UniversalDataTableColumn<T>[] {
  if (!rowSelection) return columns;
  return [
    buildUniversalDataTableSelectionColumn(rowSelection.controller, {
      title: rowSelection.title,
      selectAllAriaLabel: rowSelection.selectAllAriaLabel,
      rowAriaLabel: rowSelection.rowAriaLabel,
    }),
    ...columns,
  ];
}

/**
 * Universal Server-Side DataTable — sortable data columns via column config.
 * Set `sortable: false` only on Actions columns.
 * Responsive priority + expand via ResponsiveDataTable (ADR-032).
 */
export function UniversalDataTable<T>(props: UniversalDataTableProps<T>) {
  const { columns, rowKey, emptyState, className } = props;

  if ("table" in props && props.table) {
    const { table, toolbar, skeletonCols, rowSelection, showPagination } = props;
    const resolvedColumns = withSelectionColumn(columns, rowSelection);
    const dataColumns = resolvedColumns.filter((column) => column.sortable !== false).length;
    const selectionColCount = rowSelection ? 1 : 0;
    const showEmpty = !table.loading && !table.error && table.items.length === 0;

    return (
      <ServerDataTableFrame
        table={table}
        toolbar={toolbar}
        showPagination={showPagination}
        skeletonCols={skeletonCols ?? Math.max(dataColumns + selectionColCount + 1, 4)}
      >
        {showEmpty && emptyState ? (
          emptyState
        ) : (
          <ResponsiveDataTable
            columns={mapColumns(resolvedColumns)}
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
    <div className="server-data-table-frame">
      <div className="server-data-table-body">
        <ResponsiveDataTable
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
      </div>
    </div>
  );
}
