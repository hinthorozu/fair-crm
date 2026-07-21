import React from "react";

export interface TableRowActionsProps {
  children: React.ReactNode;
  className?: string;
  /** Accessible label for the actions group. */
  ariaLabel?: string;
}

/**
 * Shared Actions column cell wrapper (ADR-032).
 * Prefer `btn link` / `btn link danger` children; keep kebab menus as domain specialty.
 */
export function TableRowActions({
  children,
  className = "",
  ariaLabel = "Satır işlemleri",
}: TableRowActionsProps) {
  return (
    <div
      className={["table-actions", className].filter(Boolean).join(" ")}
      role="group"
      aria-label={ariaLabel}
    >
      {children}
    </div>
  );
}
