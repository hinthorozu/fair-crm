import React from "react";
import { listImportBatchesTable } from "../api/dataIntegration";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { importBatchStatusLabels } from "../labels/importLabels";
import type { ImportBatch } from "../types/import";
import { importBatchStatusBadgeVariant } from "../utils/importBadges";

interface DataIntegrationImportsPageProps {
  onNewImport: () => void;
  onOpenBatch?: (batchId: string) => void;
}

const IMPORT_COLUMNS = (
  onOpenBatch?: (batchId: string) => void,
): UniversalDataTableColumn<ImportBatch>[] => [
  {
    key: "file_name",
    title: dataIntegrationLabels.colFile,
    sortable: true,
    render: (batch) => (
      <button type="button" className="link-button" onClick={() => onOpenBatch?.(batch.id)}>
        {batch.file_name}
      </button>
    ),
  },
  {
    key: "status",
    title: dataIntegrationLabels.colStatus,
    sortable: true,
    render: (batch) => (
      <Badge variant={importBatchStatusBadgeVariant(batch.status)}>
        {importBatchStatusLabels[batch.status] ?? batch.status}
      </Badge>
    ),
  },
  {
    key: "total_rows",
    title: dataIntegrationLabels.colRows,
    sortable: true,
    render: (batch) => batch.total_rows,
  },
  {
    key: "created_at",
    title: dataIntegrationLabels.colCreated,
    sortable: true,
    render: (batch) => new Date(batch.created_at).toLocaleString("tr-TR"),
  },
];

export function DataIntegrationImportsPage({ onNewImport, onOpenBatch }: DataIntegrationImportsPageProps) {
  const table = useServerDataTable<ImportBatch>({
    fetchFn: listImportBatchesTable,
    defaultSort: { field: "created_at", direction: "desc" },
    urlSync: true,
    urlPath: "/data-integration/imports",
  });

  const columns = React.useMemo(() => IMPORT_COLUMNS(onOpenBatch), [onOpenBatch]);

  return (
    <div>
      <PageHeader
        title={dataIntegrationLabels.importsTitle}
        subtitle={dataIntegrationLabels.moduleSubtitle}
        actions={[{ id: "new-import", label: dataIntegrationLabels.newImport, onClick: onNewImport, variant: "primary" }]}
      />

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(batch) => batch.id}
        skeletonCols={4}
        emptyState={<EmptyState title={dataIntegrationLabels.importsEmpty} description="" />}
      />
      {table.error && <p className="form-error">{table.error}</p>}
    </div>
  );
}
