import React from "react";
import { DataTable, type DataTableColumn } from "./DataTable";
import type { SortDirection } from "../../types/listTable";
import { uiLabels } from "../../labels/uiLabels";
import { useViewportTier } from "../../hooks/useViewportTier";

export type ColumnPriority = "primary" | "secondary" | "technical";

export interface ResponsiveDataTableColumn<T> {
  id: string;
  header: React.ReactNode;
  sortable?: boolean;
  sortField?: string;
  render: (row: T) => React.ReactNode;
  className?: string;
  dataLabel?: string;
  /**
   * primary — always visible in main row
   * secondary — desktop main row; tablet/mobile in expand panel
   * technical — never in main row; only expand panel
   */
  priority?: ColumnPriority;
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

function columnLabel<T>(column: ResponsiveDataTableColumn<T>): string {
  if (column.dataLabel) return column.dataLabel;
  if (typeof column.header === "string") return column.header;
  return column.id;
}

function priorityClass(priority: ColumnPriority | undefined): string {
  if (priority === "secondary") return "col-priority-secondary";
  if (priority === "technical") return "col-priority-technical";
  return "";
}

/**
 * DataTable with column priority + expand child rows (ADR-032).
 * Desktop: primary + secondary; expand for technical.
 * Tablet/mobile: primary + expand for secondary/technical.
 */
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
  const tier = useViewportTier();
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(() => new Set());

  const secondaryColumns = React.useMemo(
    () => columns.filter((column) => column.priority === "secondary"),
    [columns],
  );
  const technicalColumns = React.useMemo(
    () => columns.filter((column) => column.priority === "technical"),
    [columns],
  );

  const detailColumns =
    tier === "laptop"
      ? technicalColumns
      : [...secondaryColumns, ...technicalColumns];

  const hasExpandableContent = detailColumns.length > 0;

  const toggleExpanded = React.useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const mappedColumns = React.useMemo((): DataTableColumn<T>[] => {
    const visible = columns.filter((column) => column.priority !== "technical");
    const dataColumns: DataTableColumn<T>[] = visible.map((column) => ({
      id: column.id,
      header: column.header,
      sortable: column.sortable,
      sortField: column.sortField,
      render: column.render,
      className: [column.className, priorityClass(column.priority)].filter(Boolean).join(" "),
      dataLabel: column.dataLabel ?? (typeof column.header === "string" ? column.header : undefined),
    }));

    if (!hasExpandableContent) return dataColumns;

    const expandColumn: DataTableColumn<T> = {
      id: "__expand",
      header: "",
      sortable: false,
      className: "table-expand-col",
      dataLabel: "",
      render: (row) => {
        const id = rowKey(row);
        const open = expandedIds.has(id);
        return (
          <button
            type="button"
            className="table-expand-btn"
            aria-expanded={open}
            aria-label={open ? uiLabels.collapseRow : uiLabels.expandRow}
            onClick={(event) => {
              event.stopPropagation();
              toggleExpanded(id);
            }}
          >
            {open ? "−" : "+"}
          </button>
        );
      },
    };

    return [expandColumn, ...dataColumns];
  }, [columns, expandedIds, hasExpandableContent, rowKey, toggleExpanded]);

  const renderAfterRow = React.useCallback(
    (row: T) => {
      if (!hasExpandableContent) return null;
      const id = rowKey(row);
      if (!expandedIds.has(id)) return null;

      const colSpan = mappedColumns.length;

      return (
        <tr key={`${id}__child`} className="table-child-row">
          <td colSpan={colSpan}>
            <div className="table-child-row-panel">
              {detailColumns.map((column) => (
                <div
                  key={column.id}
                  className={`table-child-field${column.priority === "technical" ? " table-child-field--technical" : ""}`}
                >
                  <span className="table-child-field-label">{columnLabel(column)}</span>
                  <div className="table-child-field-value">{column.render(row)}</div>
                </div>
              ))}
            </div>
          </td>
        </tr>
      );
    },
    [detailColumns, expandedIds, hasExpandableContent, mappedColumns.length, rowKey],
  );

  return (
    <DataTable
      columns={mappedColumns}
      data={data}
      rowKey={rowKey}
      sorting={sorting}
      loading={loading}
      error={error}
      onSortChange={onSortChange}
      onRetry={onRetry}
      emptyState={emptyState}
      className={className}
      rowClassName={() => "data-table-main-row"}
      renderAfterRow={hasExpandableContent ? renderAfterRow : undefined}
    />
  );
}
