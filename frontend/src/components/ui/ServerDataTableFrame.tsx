import React from "react";
import { PaginationBar } from "../Pagination";
import { TableSkeleton } from "./LoadingState";
import type { ServerDataTableController } from "../../hooks/useServerDataTable";

interface ServerDataTableFrameProps<T> {
  table: ServerDataTableController<T>;
  toolbar?: React.ReactNode;
  children: React.ReactNode;
  skeletonCols?: number;
  skeletonRows?: number;
  /** When false, pagination is omitted (e.g. when rendered inside `toolbar`). */
  showPagination?: boolean;
}

export function ServerDataTableFrame<T>({
  table,
  toolbar,
  children,
  skeletonCols = 6,
  skeletonRows = 6,
  showPagination = true,
}: ServerDataTableFrameProps<T>) {
  const showToolbarPanel = Boolean(toolbar) || showPagination;

  return (
    <div className="server-data-table-frame">
      {showToolbarPanel ? (
        <div className="server-data-table-toolbar-panel">
          {toolbar ? <div className="server-data-table-toolbar-filters">{toolbar}</div> : null}
          {showPagination ? (
            <div className="server-data-table-toolbar-pagination">
              <PaginationBar
                className="server-data-table-pagination"
                page={table.pagination.page}
                pageSize={table.pagination.pageSize}
                total={table.pagination.totalItems}
                totalPages={table.pagination.totalPages}
                loading={table.loading}
                onPageChange={table.setPage}
                onPageSizeChange={table.setPageSize}
              />
            </div>
          ) : null}
        </div>
      ) : null}
      {table.error && (
        <div className="banner error">
          {table.error}
          <button type="button" className="btn link" onClick={() => void table.refresh()}>
            Tekrar Dene
          </button>
        </div>
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
    </div>
  );
}
