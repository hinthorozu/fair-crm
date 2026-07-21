import React from "react";
import { paginationLabels } from "../labels";
import { PAGE_SIZE_OPTIONS } from "../types/pagination";
import { SelectInput } from "./ui/form";

export interface PaginationBarProps {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  className?: string;
}

export function PaginationBar({
  page,
  pageSize,
  total,
  totalPages,
  loading = false,
  onPageChange,
  onPageSizeChange,
  className,
}: PaginationBarProps) {
  const safeTotalPages = totalPages > 0 ? totalPages : total > 0 ? 1 : 0;
  const displayTotal = Number.isFinite(total) ? total : 0;
  const canGoPrev = page > 1 && !loading;
  const canGoNext = safeTotalPages > 0 && page < safeTotalPages && !loading;

  return (
    <div
      className={["pagination-bar", className].filter(Boolean).join(" ")}
      aria-label={paginationLabels.ariaLabel}
    >
      <div className="pagination-info">
        <span>
          {paginationLabels.pageOf(page, safeTotalPages || 1)}
        </span>
        <span className="muted">{paginationLabels.totalRecords(displayTotal)}</span>
      </div>

      <div className="pagination-controls">
        <label className="pagination-size" htmlFor="pagination-page-size">
          <span>{paginationLabels.pageSizeLabel}</span>
          <SelectInput
            id="pagination-page-size"
            value={pageSize}
            disabled={loading}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </SelectInput>
        </label>

        <div className="pagination-nav">
          <button
            type="button"
            className="btn secondary"
            disabled={!canGoPrev}
            onClick={() => onPageChange(page - 1)}
          >
            {paginationLabels.previous}
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={!canGoNext}
            onClick={() => onPageChange(page + 1)}
          >
            {paginationLabels.next}
          </button>
        </div>
      </div>
    </div>
  );
}
