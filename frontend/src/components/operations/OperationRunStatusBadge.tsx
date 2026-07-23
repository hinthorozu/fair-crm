import React from "react";
import { Badge } from "../ui/Badge";
import {
  operationUserFacingStatusBadgeVariant,
  operationUserFacingStatusLabel,
  type OperationUserFacingStatus,
} from "../../utils/operationRunStatus";

interface OperationRunStatusBadgeProps {
  status: OperationUserFacingStatus | null | undefined;
  /** When null/undefined, render em dash instead of a badge. */
  emptyLabel?: string;
}

/** Shared badge for Operation Engine user-facing run status (all automation types). */
export function OperationRunStatusBadge({
  status,
  emptyLabel = "—",
}: OperationRunStatusBadgeProps) {
  if (!status) {
    return <span className="text-muted">{emptyLabel}</span>;
  }
  return (
    <Badge variant={operationUserFacingStatusBadgeVariant(status)}>
      {operationUserFacingStatusLabel(status)}
    </Badge>
  );
}
