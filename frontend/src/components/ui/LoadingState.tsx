import React from "react";
import { labels } from "../../labels";
import { Banner } from "./Banner";

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

/** True while the first successful payload is still pending (initial load). */
export function isInitialAsyncLoad(loading: boolean, hasData: boolean): boolean {
  return loading && !hasData;
}

/**
 * Server table skeleton: initial load and deliberate query changes (not silent background refresh).
 * @see FRONTEND_UI_MASTER_STANDARD.md §11
 */
export function shouldShowServerTableLoadingSkeleton(
  loading: boolean,
  isRefreshing: boolean,
): boolean {
  return loading && !isRefreshing;
}

interface InitialLoadGateProps {
  loading: boolean;
  hasData: boolean;
  error?: string | null;
  message?: string;
  children: React.ReactNode;
  errorFallback?: React.ReactNode;
}

/**
 * Canonical initial-load wrapper: loading → `LoadingState`; error without data → `Banner`;
 * otherwise children (incl. empty states after a successful empty response).
 */
export function InitialLoadGate({
  loading,
  hasData,
  error,
  message,
  children,
  errorFallback,
}: InitialLoadGateProps) {
  if (error && !hasData) {
    return (
      errorFallback ?? (
        <Banner variant="error" role="alert">
          {error}
        </Banner>
      )
    );
  }
  if (isInitialAsyncLoad(loading, hasData)) {
    return <LoadingState message={message} />;
  }
  return <>{children}</>;
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
