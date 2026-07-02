import React from "react";
import type { SortDirection } from "../../types/listTable";

export interface DataTableColumn<T> {
  id: string;
  header: React.ReactNode;
  sortable?: boolean;
  sortField?: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

interface SortableHeaderProps {
  label: React.ReactNode;
  field: string;
  activeField: string | null;
  direction: SortDirection | null;
  onSort: (field: string) => void;
}

export function SortableHeader({
  label,
  field,
  activeField,
  direction,
  onSort,
}: SortableHeaderProps) {
  const isActive = activeField === field;
  const indicator = !isActive ? "↕" : direction === "asc" ? "↑" : "↓";
  return (
    <button
      type="button"
      className={`table-sort-header${isActive ? " active" : ""}`}
      onClick={() => onSort(field)}
    >
      <span>{label}</span>
      <span className="table-sort-indicator" aria-hidden>
        {indicator}
      </span>
    </button>
  );
}

/** Renders a sortable column header or plain text when sorting is unavailable. */
export function renderSortableHeader(
  label: React.ReactNode,
  field: string,
  sortField: string | null | undefined,
  sortDirection: SortDirection | null | undefined,
  onSortChange?: (field: string) => void,
): React.ReactNode {
  if (!onSortChange) return label;
  return (
    <SortableHeader
      label={label}
      field={field}
      activeField={sortField ?? null}
      direction={sortDirection ?? null}
      onSort={onSortChange}
    />
  );
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
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

export function DataTable<T>({
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
}: DataTableProps<T>) {
  if (error) {
    return (
      <div className="table-error-state">
        <p>{error}</p>
        {onRetry && (
          <button type="button" className="btn secondary" onClick={onRetry}>
            Tekrar Dene
          </button>
        )}
      </div>
    );
  }

  if (!loading && data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  const activeField = sorting?.field ?? null;
  const direction = sorting?.direction ?? null;

  return (
    <div className={`table-wrap ${loading ? "table-loading" : ""} ${className}`.trim()}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.id} className={column.className}>
                {column.sortable && onSortChange ? (
                  <SortableHeader
                    label={column.header}
                    field={column.sortField ?? column.id}
                    activeField={activeField}
                    direction={direction}
                    onSort={onSortChange}
                  />
                ) : (
                  column.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.id} className={column.className}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Legacy shell for static table markup during migration. */
export function DataTableShell({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`table-wrap ${className}`.trim()}>
      <table className="data-table">{children}</table>
    </div>
  );
}
