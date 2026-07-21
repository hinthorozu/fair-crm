import React from "react";

interface FormGridProps {
  children: React.ReactNode;
  className?: string;
  /** Desktop column count before responsive collapse. Default 3 (ADR-032). */
  columns?: 2 | 3;
}

export function FormGrid({ children, className, columns = 3 }: FormGridProps) {
  const colsClass = columns === 2 ? "form-grid--cols-2" : "form-grid--cols-3";
  return <div className={`form-grid ${colsClass} ${className ?? ""}`.trim()}>{children}</div>;
}
