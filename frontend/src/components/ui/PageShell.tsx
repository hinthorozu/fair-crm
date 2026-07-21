import React from "react";

export interface PageShellProps {
  children: React.ReactNode;
  className?: string;
  /** When true, content can use full shell width (no max-width clamp). */
  fullWidth?: boolean;
}

/**
 * Standard in-app page container (P3).
 * Applies `.page` + optional domain class and ultrawide max-width clamp.
 */
export function PageShell({ children, className = "", fullWidth = false }: PageShellProps) {
  return (
    <div
      className={["page", "page-shell", fullWidth ? "page-shell--full" : "", className]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}
