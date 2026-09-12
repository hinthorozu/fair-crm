import React from "react";
import { usePermissions } from "../hooks/usePermissions";
import {
  PERMISSION_IMPORTS_READ,
  PERMISSION_IMPORTS_UPDATE,
} from "../permissions/navigationPermissions";
import { ScraperRunHistoryPage as PageShellBackedScraperRunHistoryPage } from "./ScraperRunHistoryPageLegacy";

type ScraperRunHistoryPageProps = React.ComponentProps<typeof PageShellBackedScraperRunHistoryPage>;

export function ScraperRunHistoryPage(props: ScraperRunHistoryPageProps) {
  const { can } = usePermissions();
  const canContinueImport =
    can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE);

  return (
    <PageShellBackedScraperRunHistoryPage
      {...props}
      onOpenImportBatch={canContinueImport ? props.onOpenImportBatch : undefined}
    />
  );
}
