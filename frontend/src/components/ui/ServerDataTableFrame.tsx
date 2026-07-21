import React from "react";
import { PaginationBar } from "../Pagination";
import { TableSkeleton } from "./LoadingState";
import type { ServerDataTableController } from "../../hooks/useServerDataTable";
import { Banner } from "./Banner";

interface ServerDataTableFrameProps<T> {
  table: ServerDataTableController<T>;
  toolbar?: React.ReactNode;
  children: React.ReactNode;
  skeletonCols?: number;
  skeletonRows?: number;
  /** When false, top pagination is omitted (e.g. when rendered inside `toolbar`). */
  showPagination?: boolean;
  /**
   * When true (default), renders the same PaginationBar below the table body.
   * Set false only for rare nested/preview frames that must stay top-only.
   */
  showBottomPagination?: boolean;
}

/** Shared PaginationBar wired to a server-side table controller (single source of state). */
export function ServerDataTablePagination<T>({
  table,
  className = "server-data-table-pagination",
}: {
  table: ServerDataTableController<T>;
  className?: string;
}) {
  return (
    <PaginationBar
      className={className}
      page={table.pagination.page}
      pageSize={table.pagination.pageSize}
      total={table.pagination.totalItems}
      totalPages={table.pagination.totalPages}
      loading={table.loading}
      onPageChange={table.setPage}
      onPageSizeChange={table.setPageSize}
    />
  );
}

export function ServerDataTableFrame<T>({
  table,
  toolbar,
  children,
  skeletonCols = 6,
  skeletonRows = 6,
  showPagination = true,
  showBottomPagination = true,
}: ServerDataTableFrameProps<T>) {
  const showToolbarPanel = Boolean(toolbar) || showPagination;
  const showBottom = showBottomPagination && showPagination;

  return (
    <div className="server-data-table-frame">
      {showToolbarPanel ? (
        <div className="server-data-table-toolbar-panel">
          {toolbar ? <div className="server-data-table-toolbar-slot">{toolbar}</div> : null}
          {showPagination ? (
            <div className="server-data-table-toolbar-pagination">
              <ServerDataTablePagination table={table} />
            </div>
          ) : null}
        </div>
      ) : null}
      {table.error && (
        <Banner variant="error">
          {table.error}
          <button type="button" className="btn link" onClick={() => void table.refresh()}>
            Tekrar Dene
          </button>
        </Banner>
      )}
      <div className="server-data-table-body">
        {table.loading ? (
          <div className="table-wrap table-skeleton-wrap">
            <TableSkeleton rows={skeletonRows} cols={skeletonCols} />
          </div>
        ) : (
          children
        )}
      </div>
      {showBottom ? (
        <div className="server-data-table-bottom-pagination">
          <ServerDataTablePagination table={table} />
        </div>
      ) : null}
    </div>
  );
}
