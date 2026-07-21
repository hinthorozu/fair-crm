import React from "react";
import { DataTable, type DataTableColumn } from "./DataTable";
import type { SortDirection } from "../../types/listTable";
import { uiLabels } from "../../labels/uiLabels";
import { IconButton } from "./IconButton";

/**
 * Column order = responsive priority (DataTables Responsive style).
 * Index 0 is highest priority; last columns hide first when space runs out.
 */
export interface WidthResponsiveColumn<T> {
  id: string;
  header: React.ReactNode;
  sortable?: boolean;
  sortField?: string;
  render: (row: T) => React.ReactNode;
  className?: string;
  /** Label shown in child-row details (defaults to string header / id). */
  dataLabel?: string;
  /** Prefer wrapping at word boundaries instead of nowrap (e.g. company name). */
  allowWrap?: boolean;
}

interface WidthResponsiveDataTableProps<T> {
  /** Main-row candidates; order = hide priority (trailing hides first). */
  columns: WidthResponsiveColumn<T>[];
  /**
   * Detail-only columns (legacy `priority: "technical"`).
   * Never shown in the main row; appear in the child row when expand is open.
   */
  detailOnlyColumns?: WidthResponsiveColumn<T>[];
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

const EXPAND_COL_ID = "__expand";
const EXPAND_COL_FALLBACK_PX = 44;
const MIN_COL_FALLBACK_PX = 72;
/** Border/padding/font metric slack so live row never exceeds the wrap. */
const CONTAINER_SAFETY_PX = 40;

function columnLabel<T>(column: WidthResponsiveColumn<T>): string {
  if (column.dataLabel) return column.dataLabel;
  if (typeof column.header === "string") return column.header;
  return column.id;
}

/**
 * Pick how many leading columns fit in `availableWidth` given measured min widths.
 * When any column must hide (or detail-only exists), `expandWidth` is reserved.
 */
export function resolveVisibleColumnCount(
  columnMinWidths: number[],
  containerWidth: number,
  expandWidth: number,
  options?: { forceExpandReserve?: boolean },
): number {
  const forceExpandReserve = options?.forceExpandReserve === true;
  const count = columnMinWidths.length;
  if (count === 0) return 0;
  if (containerWidth <= 0) return Math.min(1, count);

  const total = columnMinWidths.reduce((sum, width) => sum + width, 0);
  if (total <= containerWidth && !forceExpandReserve) return count;

  const budget = Math.max(containerWidth - expandWidth, 0);
  let used = 0;
  let visible = 0;
  for (let index = 0; index < count; index += 1) {
    const next = columnMinWidths[index] ?? MIN_COL_FALLBACK_PX;
    if (used + next <= budget) {
      used += next;
      visible += 1;
    } else {
      break;
    }
  }
  return Math.max(visible, count > 0 ? 1 : 0);
}

/**
 * FAIR CRM default table engine (ADR-032): available-width column hiding + child rows.
 * Column order = responsive priority. No fixed mobile/tablet breakpoint layouts.
 */
export function WidthResponsiveDataTable<T>({
  columns,
  detailOnlyColumns = [],
  data,
  rowKey,
  sorting,
  loading = false,
  error,
  onSortChange,
  onRetry,
  emptyState,
  className = "",
}: WidthResponsiveDataTableProps<T>) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const measureTableRef = React.useRef<HTMLTableElement>(null);
  const [containerWidth, setContainerWidth] = React.useState(0);
  const [columnMinWidths, setColumnMinWidths] = React.useState<number[]>([]);
  const [expandWidth, setExpandWidth] = React.useState(EXPAND_COL_FALLBACK_PX);
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(() => new Set());

  const hasDetailOnly = detailOnlyColumns.length > 0;

  const measureColumnWidths = React.useCallback(() => {
    const table = measureTableRef.current;
    if (!table) return;
    const headerCells = table.querySelectorAll<HTMLTableCellElement>("thead th[data-measure-col]");
    if (headerCells.length === 0) return;

    const widths: number[] = [];
    headerCells.forEach((th) => {
      const bodyCells = table.querySelectorAll<HTMLTableCellElement>(
        `tbody td[data-measure-col="${th.dataset.measureCol}"]`,
      );
      let maxWidth = th.getBoundingClientRect().width;
      bodyCells.forEach((td) => {
        maxWidth = Math.max(maxWidth, td.getBoundingClientRect().width);
      });
      widths.push(Math.ceil(maxWidth));
    });

    const expandTh = table.querySelector<HTMLTableCellElement>("thead th[data-measure-expand]");
    if (expandTh) {
      setExpandWidth(Math.max(EXPAND_COL_FALLBACK_PX, Math.ceil(expandTh.getBoundingClientRect().width)));
    }

    if (widths.length === columns.length) {
      setColumnMinWidths(widths);
    }
  }, [columns.length]);

  React.useLayoutEffect(() => {
    measureColumnWidths();
  }, [measureColumnWidths, data, columns]);

  React.useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === "undefined") {
      setContainerWidth(node?.clientWidth ?? 0);
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setContainerWidth(Math.floor(entry.contentRect.width));
      requestAnimationFrame(() => measureColumnWidths());
    });
    observer.observe(node);
    setContainerWidth(node.clientWidth);
    return () => observer.disconnect();
  }, [measureColumnWidths]);

  const widthsForResolve =
    columnMinWidths.length === columns.length
      ? columnMinWidths
      : columns.map(() => MIN_COL_FALLBACK_PX);

  const visibleCount = resolveVisibleColumnCount(
    widthsForResolve,
    Math.max(0, containerWidth - CONTAINER_SAFETY_PX),
    expandWidth,
    { forceExpandReserve: hasDetailOnly },
  );
  const hiddenColumns = React.useMemo(
    () => columns.slice(visibleCount),
    [columns, visibleCount],
  );
  const visibleColumns = React.useMemo(
    () => columns.slice(0, visibleCount),
    [columns, visibleCount],
  );
  const childColumns = React.useMemo(
    () => [...hiddenColumns, ...detailOnlyColumns],
    [detailOnlyColumns, hiddenColumns],
  );
  const hasChildContent = childColumns.length > 0;

  React.useEffect(() => {
    if (!hasChildContent) {
      setExpandedIds(new Set());
    }
  }, [hasChildContent]);

  const toggleExpanded = React.useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const mappedColumns = React.useMemo((): DataTableColumn<T>[] => {
    const dataColumns: DataTableColumn<T>[] = visibleColumns.map((column) => ({
      id: column.id,
      header: column.header,
      sortable: column.sortable,
      sortField: column.sortField,
      render: column.render,
      className: [column.className, column.allowWrap ? "col-wrap" : "col-nowrap"]
        .filter(Boolean)
        .join(" "),
      dataLabel: columnLabel(column),
    }));

    if (!hasChildContent) return dataColumns;

    const expandColumn: DataTableColumn<T> = {
      id: EXPAND_COL_ID,
      header: "",
      sortable: false,
      className: "table-expand-col col-nowrap",
      dataLabel: "",
      render: (row) => {
        const id = rowKey(row);
        const open = expandedIds.has(id);
        return (
          <IconButton
            variant="table"
            label={open ? uiLabels.collapseRow : uiLabels.expandRow}
            icon={open ? "−" : "+"}
            pressed={open}
            aria-expanded={open}
            onClick={(event) => {
              event.stopPropagation();
              toggleExpanded(id);
            }}
          />
        );
      },
    };

    return [expandColumn, ...dataColumns];
  }, [expandedIds, hasChildContent, rowKey, toggleExpanded, visibleColumns]);

  const renderAfterRow = React.useCallback(
    (row: T) => {
      if (!hasChildContent) return null;
      const id = rowKey(row);
      if (!expandedIds.has(id)) return null;

      return (
        <tr key={`${id}__child`} className="table-child-row">
          <td colSpan={mappedColumns.length}>
            <div className="table-child-row-panel">
              {childColumns.map((column) => (
                <div key={column.id} className="table-child-field">
                  <span className="table-child-field-label">{columnLabel(column)}:</span>{" "}
                  <span className="table-child-field-value">{column.render(row)}</span>
                </div>
              ))}
            </div>
          </td>
        </tr>
      );
    },
    [childColumns, expandedIds, hasChildContent, mappedColumns.length, rowKey],
  );

  const measureSample = data.slice(0, Math.min(3, data.length));

  return (
    <div className="width-responsive-table-root" ref={containerRef}>
      <div className="width-responsive-measure" aria-hidden="true">
        <table className="data-table" ref={measureTableRef}>
          <thead>
            <tr>
              <th data-measure-expand className="table-expand-col">
                <span className="table-expand-btn">+</span>
              </th>
              {columns.map((column) => (
                <th
                  key={column.id}
                  data-measure-col={column.id}
                  className={[column.className, column.allowWrap ? "col-wrap" : "col-nowrap"]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {measureSample.map((row) => (
              <tr key={`measure-${rowKey(row)}`}>
                <td className="table-expand-col">
                  <span className="table-expand-btn">+</span>
                </td>
                {columns.map((column) => (
                  <td
                    key={column.id}
                    data-measure-col={column.id}
                    className={[column.className, column.allowWrap ? "col-wrap" : "col-nowrap"]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
        className={`table-wrap--width-responsive ${className}`.trim()}
        rowClassName={() => "data-table-main-row"}
        renderAfterRow={hasChildContent ? renderAfterRow : undefined}
      />
    </div>
  );
}
