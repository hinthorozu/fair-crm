import React from "react";

export interface FieldErrorProps {
  children: React.ReactNode;
  className?: string;
  as?: "p" | "span" | "dd";
}

/**
 * Standalone field / modal validation error (ADR-032).
 * Prefer FormField `error=` when wrapping a labeled control.
 * Page/section fetch errors should use Banner, not FieldError.
 */
export function FieldError({ children, className = "", as: Tag = "p" }: FieldErrorProps) {
  if (children == null || children === false || children === "") return null;
  return (
    <Tag className={["field-error", className].filter(Boolean).join(" ")} role="alert">
      {children}
    </Tag>
  );
}
