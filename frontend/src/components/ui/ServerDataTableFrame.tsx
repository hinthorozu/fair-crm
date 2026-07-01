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
}

export function ServerDataTableFrame<T>({
  table,
  toolbar,
  children,
  skeletonCols = 6,
  skeletonRows = 6,
}: ServerDataTableFrameProps<T>) {
  return (
    <>
      {toolbar}
      {table.error && (
        <div className="banner error">
          {table.error}
          <button type="button" className="btn link" onClick={() => void table.refresh()}>
            Tekrar Dene
          </button>
        </div>
      )}
      <PaginationBar
        page={table.pagination.page}
        pageSize={table.pagination.pageSize}
        total={table.pagination.totalItems}
        totalPages={table.pagination.totalPages}
        loading={table.loading}
        onPageChange={table.setPage}
        onPageSizeChange={table.setPageSize}
      />
      {table.loading ? (
        <TableSkeleton rows={skeletonRows} cols={skeletonCols} />
      ) : (
        children
      )}
    </>
  );
}
