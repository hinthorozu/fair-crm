import React from "react";
import {
  deleteImportBatch,
  getImportJob,
  listImportBatchesTable,
  startImportAnalyzeJob,
} from "../api/dataIntegration";
import { ApiError } from "../api/client";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { importBatchStatusLabels } from "../labels/importLabels";
import type { ImportBatch } from "../types/import";
import { importBatchStatusBadgeVariant } from "../utils/importBadges";
import { canResumeDecisions, canResumeSetup } from "../utils/importResume";

interface DataIntegrationImportsPageProps {
  onNewImport: () => void;
  onOpenBatch?: (batchId: string) => void;
  onContinueBatch?: (batchId: string) => void;
}

function canAnalyze(status: string): boolean {
  return status === "mapping_completed" || status === "mapped" || status === "analysis_failed";
}

function showContinue(status: string): boolean {
  return canResumeSetup(status) || canResumeDecisions(status);
}

function isOperationInProgress(status: string): boolean {
  return (
    status === "analyzing" ||
    status === "analysis_queued" ||
    status === "applying"
  );
}

const IMPORT_COLUMNS = (
  handlers: {
    onOpenBatch?: (batchId: string) => void;
    onContinueBatch?: (batchId: string) => void;
    onAnalyze?: (batch: ImportBatch) => void;
    onDelete?: (batch: ImportBatch) => void;
    analyzingBatchId?: string | null;
    deletingBatchId?: string | null;
  },
): UniversalDataTableColumn<ImportBatch>[] => [
  {
    key: "file_name",
    title: dataIntegrationLabels.colFile,
    sortable: true,
    render: (batch) => (
      <button type="button" className="link-button" onClick={() => handlers.onOpenBatch?.(batch.id)}>
        {batch.file_name}
      </button>
    ),
  },
  {
    key: "status",
    title: dataIntegrationLabels.colStatus,
    sortable: true,
    render: (batch) => (
      <div className="import-list-status">
        <Badge variant={importBatchStatusBadgeVariant(batch.status)}>
          {importBatchStatusLabels[batch.status] ?? batch.status}
        </Badge>
        {batch.status === "analysis_failed" && batch.notes ? (
          <span className="text-muted import-list-error" title={batch.notes}>
            {batch.notes}
          </span>
        ) : null}
      </div>
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
  {
    key: "actions",
    title: dataIntegrationLabels.colActions,
    sortable: false,
    render: (batch) => (
      <div className="import-list-actions">
        {canAnalyze(batch.status) && (
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={handlers.analyzingBatchId === batch.id}
            onClick={() => handlers.onAnalyze?.(batch)}
          >
            {handlers.analyzingBatchId === batch.id ? "Analiz ediliyor…" : "Analiz Yap"}
          </button>
        )}
        {isOperationInProgress(batch.status) && (
          <span className="text-muted">İşlem devam ediyor…</span>
        )}
        {showContinue(batch.status) && (
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            onClick={() => handlers.onContinueBatch?.(batch.id)}
          >
            {dataIntegrationLabels.continueBatch}
          </button>
        )}
        <button
          type="button"
          className="btn btn-sm danger"
          disabled={
            isOperationInProgress(batch.status) ||
            handlers.analyzingBatchId === batch.id ||
            handlers.deletingBatchId === batch.id
          }
          onClick={() => handlers.onDelete?.(batch)}
        >
          {handlers.deletingBatchId === batch.id
            ? "Siliniyor…"
            : dataIntegrationLabels.deleteBatch}
        </button>
      </div>
    ),
  },
];

export function DataIntegrationImportsPage({
  onNewImport,
  onOpenBatch,
  onContinueBatch,
}: DataIntegrationImportsPageProps) {
  const [analyzingBatchId, setAnalyzingBatchId] = React.useState<string | null>(null);
  const [deletingBatchId, setDeletingBatchId] = React.useState<string | null>(null);
  const [batchToDelete, setBatchToDelete] = React.useState<ImportBatch | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);

  const table = useServerDataTable<ImportBatch>({
    fetchFn: listImportBatchesTable,
    defaultSort: { field: "created_at", direction: "desc" },
    urlSync: true,
    urlPath: "/data-integration/imports",
  });

  React.useEffect(() => {
    if (!successMessage) return;
    const timer = window.setTimeout(() => setSuccessMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [successMessage]);

  const handleAnalyze = React.useCallback(
    async (batch: ImportBatch) => {
      setActionError(null);
      setAnalyzingBatchId(batch.id);
      try {
        const job = await startImportAnalyzeJob(batch.id);
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          const status = await getImportJob(job.job_id);
          if (status.status === "completed") {
            await table.refresh();
            return;
          }
          if (status.status === "failed") {
            throw new ApiError(status.error_message ?? "Analiz başarısız", 500, status);
          }
          await new Promise((r) => window.setTimeout(r, 800));
        }
        throw new ApiError("Analiz zaman aşımına uğradı", 504);
      } catch (err) {
        setActionError(err instanceof ApiError ? err.message : "Analiz başlatılamadı");
        await table.refresh();
      } finally {
        setAnalyzingBatchId(null);
      }
    },
    [table],
  );

  const handleConfirmDelete = React.useCallback(async () => {
    if (!batchToDelete) return;
    setDeletingBatchId(batchToDelete.id);
    setActionError(null);
    try {
      await deleteImportBatch(batchToDelete.id);
      setBatchToDelete(null);
      setSuccessMessage(dataIntegrationLabels.deleteBatchSuccess);
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Silme işlemi başarısız");
    } finally {
      setDeletingBatchId(null);
    }
  }, [batchToDelete, table]);

  const handleOpen = onContinueBatch ?? onOpenBatch;

  const columns = React.useMemo(
    () =>
      IMPORT_COLUMNS({
        onOpenBatch: handleOpen,
        onContinueBatch: handleOpen,
        onAnalyze: (batch) => void handleAnalyze(batch),
        onDelete: setBatchToDelete,
        analyzingBatchId,
        deletingBatchId,
      }),
    [handleOpen, handleAnalyze, analyzingBatchId, deletingBatchId],
  );

  return (
    <div>
      <PageHeader
        title={dataIntegrationLabels.importsTitle}
        subtitle={dataIntegrationLabels.moduleSubtitle}
        actions={[{ id: "new-import", label: dataIntegrationLabels.newImport, onClick: onNewImport, variant: "primary" }]}
      />

      {successMessage && <p className="import-toast success">{successMessage}</p>}

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(batch) => batch.id}
        skeletonCols={5}
        emptyState={<EmptyState title={dataIntegrationLabels.importsEmpty} description="" />}
      />
      {(table.error || actionError) && (
        <p className="form-error">{actionError ?? table.error}</p>
      )}

      {batchToDelete && (
        <ConfirmDialog
          title={dataIntegrationLabels.deleteBatchTitle}
          message={dataIntegrationLabels.deleteBatchMessage}
          confirmLabel={dataIntegrationLabels.deleteBatchConfirm}
          variant="danger"
          loading={deletingBatchId === batchToDelete.id}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setBatchToDelete(null)}
        />
      )}
    </div>
  );
}
