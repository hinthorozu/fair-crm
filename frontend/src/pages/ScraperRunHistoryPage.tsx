import React from "react";
import { usePermissions } from "../hooks/usePermissions";
import {
  PERMISSION_IMPORTS_READ,
  PERMISSION_IMPORTS_UPDATE,
} from "../permissions/navigationPermissions";
import { ScraperRunHistoryPage as LegacyScraperRunHistoryPage } from "./ScraperRunHistoryPageLegacy";

type ScraperRunHistoryPageProps = React.ComponentProps<typeof LegacyScraperRunHistoryPage>;

export function ScraperRunHistoryPage(props: ScraperRunHistoryPageProps) {
  const { can } = usePermissions();
  const canContinueImport =
    can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE);

  return (
    <LegacyScraperRunHistoryPage
      {...props}
      onOpenImportBatch={canContinueImport ? props.onOpenImportBatch : undefined}
    />
  );
}
