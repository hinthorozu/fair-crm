/**
 * @deprecated Use `WidthResponsiveDataTable` via `UniversalDataTable`.
 * Kept as a thin adapter for any leftover imports; do not use in new screens.
 */
import type { ReactNode } from "react";
import {
  WidthResponsiveDataTable,
  type WidthResponsiveColumn,
} from "./WidthResponsiveDataTable";
import type { SortDirection } from "../../types/listTable";

export type ColumnPriority = "primary" | "secondary" | "technical";

export interface ResponsiveDataTableColumn<T> {
  id: string;
  header: ReactNode;
  sortable?: boolean;
  sortField?: string;
  render: (row: T) => ReactNode;
  className?: string;
  dataLabel?: string;
  /**
   * - technical → detail-only (never main row)
   * - primary / secondary → main-row candidates; array order = hide priority
   */
  priority?: ColumnPriority;
  allowWrap?: boolean;
}

interface ResponsiveDataTableProps<T> {
  columns: ResponsiveDataTableColumn<T>[];
  data: T[];
  rowKey: (row: T) => string;
  sorting?: { field: string; direction: SortDirection } | null;
  loading?: boolean;
  error?: string | null;
  onSortChange?: (field: string) => void;
  onRetry?: () => void;
  emptyState?: React.ReactNode;
  className?: string;
}

/** @deprecated Prefer UniversalDataTable → WidthResponsiveDataTable. */
export function ResponsiveDataTable<T>({
  columns,
  data,
  rowKey,
  sorting,
  loading = false,
  error,
  onSortChange,
  onRetry,
  emptyState,
  className = "",
}: ResponsiveDataTableProps<T>) {
  const main: WidthResponsiveColumn<T>[] = [];
  const detailOnly: WidthResponsiveColumn<T>[] = [];

  for (const column of columns) {
    const mapped: WidthResponsiveColumn<T> = {
      id: column.id,
      header: column.header,
      sortable: column.sortable,
      sortField: column.sortField,
      render: column.render,
      className: column.className,
      dataLabel: column.dataLabel,
      allowWrap: column.allowWrap,
    };
    if (column.priority === "technical") {
      detailOnly.push(mapped);
    } else {
      main.push(mapped);
    }
  }

  return (
    <WidthResponsiveDataTable
      columns={main}
      detailOnlyColumns={detailOnly}
      data={data}
      rowKey={rowKey}
      sorting={sorting}
      loading={loading}
      error={error}
      onSortChange={onSortChange}
      onRetry={onRetry}
      emptyState={emptyState}
      className={className}
    />
  );
}
