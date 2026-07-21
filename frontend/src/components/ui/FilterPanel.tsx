import React from "react";

export interface FilterPanelProps {
  children: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  /** Accessible label for the filter region. */
  ariaLabel?: string;
}

/**
 * Shared list filter / toolbar shell (ADR-032).
 * Fields use a responsive 3 / 2 / 1 grid; actions sit below or beside via CSS.
 */
export function FilterPanel({
  children,
  actions,
  className = "",
  ariaLabel = "Filtreler",
}: FilterPanelProps) {
  return (
    <div
      className={`filter-panel ${className}`.trim()}
      role="search"
      aria-label={ariaLabel}
    >
      <div className="filter-panel-fields">{children}</div>
      {actions ? <div className="filter-panel-actions">{actions}</div> : null}
    </div>
  );
}
