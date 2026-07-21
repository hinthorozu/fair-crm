import React from "react";

export interface TableEntityLinkProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "type" | "className"> {
  children: React.ReactNode;
  className?: string;
}

/**
 * In-table entity navigation control (customer name, todo title, file name, …).
 * Standardizes former ad-hoc `link-button` markup onto `btn link`.
 */
export function TableEntityLink({ children, className = "", ...rest }: TableEntityLinkProps) {
  return (
    <button
      type="button"
      className={["btn", "link", "table-entity-link", className].filter(Boolean).join(" ")}
      {...rest}
    >
      {children}
    </button>
  );
}
