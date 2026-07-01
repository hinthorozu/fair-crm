import React from "react";
import { labels } from "../../labels";

interface LoadingStateProps {
  message?: string;
  variant?: "inline" | "card" | "overlay";
}

export function LoadingState({ message = labels.loading, variant = "card" }: LoadingStateProps) {
  return (
    <div className={`loading-state loading-state-${variant}`} role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="table-skeleton" aria-hidden="true">
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="table-skeleton-row">
          {Array.from({ length: cols }).map((__, col) => (
            <div key={col} className="table-skeleton-cell" />
          ))}
        </div>
      ))}
    </div>
  );
}
