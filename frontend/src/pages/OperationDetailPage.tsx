import React from "react";
import { usePermissions } from "../hooks/usePermissions";
import {
  PERMISSION_IMPORTS_READ,
  PERMISSION_IMPORTS_UPDATE,
} from "../permissions/navigationPermissions";
import { OperationDetailPage as LegacyOperationDetailPage } from "./OperationDetailPageLegacy";

type OperationDetailPageProps = React.ComponentProps<typeof LegacyOperationDetailPage>;

export function OperationDetailPage(props: OperationDetailPageProps) {
  const { can } = usePermissions();
  const canContinueImport =
    can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE);

  return (
    <LegacyOperationDetailPage
      {...props}
      onOpenImportBatch={canContinueImport ? props.onOpenImportBatch : undefined}
    />
  );
}
