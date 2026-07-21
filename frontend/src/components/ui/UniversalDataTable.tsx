import React from "react";
import {
  WidthResponsiveDataTable,
  type WidthResponsiveColumn,
} from "./WidthResponsiveDataTable";
import { ServerDataTableFrame } from "./ServerDataTableFrame";
import type { ServerDataTableRowSelectionController } from "../../hooks/useServerDataTableRowSelection";
import type { ServerDataTableController } from "../../hooks/useServerDataTable";
import type { SortDirection } from "../../types/listTable";
import { buildUniversalDataTableSelectionColumn } from "./UniversalDataTableSelection";

/** @deprecated Prefer column order for priority. Keep `"technical"` for detail-only fields. */
export type ColumnPriority = "primary" | "secondary" | "technical";

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
  /** Child-row label; defaults to `title` when it is a string. */
  dataLabel?: string;
  /**
   * - `"technical"` — never in main row; child-row only (UUIDs, adapter keys, …).
   * - `"primary"` / `"secondary"` — legacy; order in `columns` is the responsive priority.
   */
  priority?: ColumnPriority;
  /** Wrap at word boundaries (inferred for name/title-like keys when omitted). */
  allowWrap?: boolean;
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
  showPagination?: never;
  showBottomPagination?: never;
}

interface UniversalDataTableServerProps<T> extends UniversalDataTableBaseProps<T> {
  table: ServerDataTableController<T>;
  toolbar?: React.ReactNode;
  skeletonCols?: number;
  showPagination?: boolean;
  /** Dual top+bottom pagination (default true). */
  showBottomPagination?: boolean;
  /** Optional row selection (ADR-029); prepends a Selection column. */
  rowSelection?: UniversalDataTableRowSelectionConfig<T & { id: string }>;
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

function inferAllowWrap(key: string, allowWrap: boolean | undefined): boolean {
  if (allowWrap != null) return allowWrap;
  return /name|title|company|subject|message|description|label|display/i.test(key);
}

function toWidthColumn<T>(column: UniversalDataTableColumn<T>): WidthResponsiveColumn<T> {
  return {
    id: column.key,
    header: column.title,
    sortable: column.sortable !== false,
    sortField: column.sortField ?? column.key,
    render: column.render,
    className: column.className,
    dataLabel:
      column.dataLabel ?? (typeof column.title === "string" ? column.title : undefined),
    allowWrap: inferAllowWrap(column.key, column.allowWrap),
  };
}

function splitColumns<T>(columns: UniversalDataTableColumn<T>[]): {
  main: WidthResponsiveColumn<T>[];
  detailOnly: WidthResponsiveColumn<T>[];
} {
  const main: WidthResponsiveColumn<T>[] = [];
  const detailOnly: WidthResponsiveColumn<T>[] = [];
  for (const column of columns) {
    const mapped = toWidthColumn(column);
    if (column.priority === "technical") {
      detailOnly.push(mapped);
    } else {
      main.push(mapped);
    }
  }
  return { main, detailOnly };
}

function withSelectionColumn<T>(
  columns: UniversalDataTableColumn<T>[],
  rowSelection: UniversalDataTableRowSelectionConfig<T & { id: string }> | undefined,
): UniversalDataTableColumn<T>[] {
  if (!rowSelection) return columns;
  const selectionCol = buildUniversalDataTableSelectionColumn(
    rowSelection.controller,
    {
      title: rowSelection.title,
      selectAllAriaLabel: rowSelection.selectAllAriaLabel,
      rowAriaLabel: rowSelection.rowAriaLabel,
    },
  ) as UniversalDataTableColumn<T>;
  return [selectionCol, ...columns];
}

function toSorting(
  sorting: { field: string | null; direction: SortDirection | null } | null | undefined,
): { field: string; direction: SortDirection } | null {
  if (!sorting?.field) return null;
  return { field: sorting.field, direction: sorting.direction ?? "asc" };
}

/**
 * Universal Server-Side DataTable — FAIR CRM default list standard (ADR-019 / ADR-032).
 *
 * - Width-responsive column hiding (column order = priority)
 * - Child row for hidden + technical columns
 * - Dual pagination when used with `table` (via ServerDataTableFrame)
 */
export function UniversalDataTable<T>(props: UniversalDataTableProps<T>) {
  const { columns, rowKey, emptyState, className } = props;

  if ("table" in props && props.table) {
    const {
      table,
      toolbar,
      skeletonCols,
      rowSelection,
      showPagination,
      showBottomPagination,
    } = props;
    const resolvedColumns = withSelectionColumn(columns, rowSelection);
    const { main, detailOnly } = splitColumns(resolvedColumns);
    const dataColumns = resolvedColumns.filter((column) => column.sortable !== false).length;
    const selectionColCount = rowSelection ? 1 : 0;
    const showEmpty = !table.loading && !table.error && table.items.length === 0;

    return (
      <ServerDataTableFrame
        table={table}
        toolbar={toolbar}
        showPagination={showPagination}
        showBottomPagination={showBottomPagination}
        skeletonCols={skeletonCols ?? Math.max(dataColumns + selectionColCount + 1, 4)}
      >
        {showEmpty && emptyState ? (
          emptyState
        ) : (
          <WidthResponsiveDataTable
            columns={main}
            detailOnlyColumns={detailOnly}
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

  const { main, detailOnly } = splitColumns(columns);

  return (
    <div className="server-data-table-frame">
      <div className="server-data-table-body">
        <WidthResponsiveDataTable
          columns={main}
          detailOnlyColumns={detailOnly}
          data={items}
          rowKey={rowKey}
          sorting={toSorting(sorting ?? null)}
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
