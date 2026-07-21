import React from "react";

interface EmptyStateProps {
  title?: string;
  /** @deprecated Prefer `title`. Kept as alias for call-site compatibility. */
  message?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({
  title,
  message,
  description,
  actionLabel,
  onAction,
  icon,
}: EmptyStateProps) {
  const heading = title ?? message ?? "";
  return (
    <div className="empty-state" role="status">
      {icon && <div className="empty-state-icon" aria-hidden="true">{icon}</div>}
      {heading ? <h3 className="empty-state-title">{heading}</h3> : null}
      {description && <p className="empty-state-description">{description}</p>}
      {actionLabel && onAction && (
        <button type="button" className="btn primary" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function EmptyStateIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <rect x="8" y="12" width="32" height="24" rx="4" stroke="currentColor" strokeWidth="2" />
      <path d="M16 20h16M16 26h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
