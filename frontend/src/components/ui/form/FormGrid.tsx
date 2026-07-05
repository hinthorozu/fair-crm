import React from "react";

interface FormGridProps {
  children: React.ReactNode;
  className?: string;
}

export function FormGrid({ children, className }: FormGridProps) {
  return <div className={`form-grid ${className ?? ""}`.trim()}>{children}</div>;
}
