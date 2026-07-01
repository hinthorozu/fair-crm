import React from "react";

interface DataTableProps {
  children: React.ReactNode;
  className?: string;
}

export function DataTable({ children, className = "" }: DataTableProps) {
  return (
    <div className={`table-wrap ${className}`.trim()}>
      <table className="data-table">{children}</table>
    </div>
  );
}
