import React from "react";

interface CommunicationListCellProps {
  value: string | null | undefined;
  extraCount?: number;
}

export function CommunicationListCell({ value, extraCount = 0 }: CommunicationListCellProps) {
  if (!value) {
    return <>—</>;
  }

  return (
    <span className="communication-list-cell">
      <span className="communication-list-cell-value">{value}</span>
      {extraCount > 0 && (
        <span className="communication-list-cell-extra muted">+{extraCount}</span>
      )}
    </span>
  );
}
