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
import { usePermissions } from "../hooks/usePermissions";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { importBatchStatusLabels } from "../labels/importLabels";
import { IMPORT_PERMISSION_UPDATE } from "../permissions/importPermissions";
import type { ImportBatch } from "../types/import";
import { importBatchStatusBadgeVariant } from "../utils/importBadges";
import {
  canAnalyzeImportBatch,
  canReanalyzeImportBatch,
  isImportBatchOperationInProgress,
  showContinueImportBatch,
} from "../utils/importListActions";
import {
  formatImportLastAnalyzedAt,
  importAnalysisStatusLabel,
} from "../utils/importAnalysisDisplay";
import { Banner } from "../components/ui/Banner";
import { TableRowActions } from "../components/ui/TableRowActions";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { TruncatedText } from "../components/ui/TruncatedText";
import { PageShell } from "../components/ui/PageShell";

const canAnalyze = canAnalyzeImportBatch;
const canReanalyze = canReanalyzeImportBatch;
const isOperationInProgress = isImportBatchOperationInProgress;
const showContinue = showContinueImportBatch;

interface DataIntegrationImportsPageProps {
  onOpenBatch?: (batchId: string) => void;
  onContinueBatch?: (batchId: string) => void;
}

function displayOptionalText(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

const IMPORT_COLUMNS = (
  handlers: {
    onOpenBatch?: (batchId: string) => void;
    onContinueBatch?: (batchId: string) => void;
    onAnalyze?: (batch: ImportBatch, options?: { reanalyze?: boolean }) => void;
    onDelete?: (batch: ImportBatch) => void;
    canUpdate: boolean;
    analyzingBatchId?: string | null;
    deletingBatchId?: string | null;
  },
): UniversalDataTableColumn<ImportBatch>[] => [
  {
    key: "file_name",
    title: dataIntegrationLabels.colFile,
    sortable: true,
    render: (batch) => (
      <TableEntityLink onClick={() => handlers.onOpenBatch?.(batch.id)}>
        {batch.file_name}
      </TableEntityLink>
    ),
  },
  {
    key: "source_type",
    title: dataIntegrationLabels.colType,
    sortable: false,
    render: (batch) =>
      dataIntegrationLabels.importSourceTypeLabels[batch.source_type] ?? batch.source_type,
  },
  {
    key: "fair_name",
    title: dataIntegrationLabels.colFair,
    sortable: false,
    render: (batch) => displayOptionalText(batch.fair_name),
  },
  {
    key: "adapter_key",
    title: dataIntegrationLabels.colAdapter,
    sortable: false,
    priority: "technical",
    render: (batch) => (
      <TruncatedText value={batch.adapter_key} mono maxLength={28} />
    ),
  },
  {
    key: "status",
    title: dataIntegrationLabels.colStatus,
    sortable: true,
    priority: "primary",
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
    key: "analysis_status",
    title: dataIntegrationLabels.colAnalysisStatus,
    sortable: false,
    priority: "primary",
    render: (batch) => importAnalysisStatusLabel(batch),
  },
  {
    key: "analyzed_at",
    title: dataIntegrationLabels.colLastAnalyzed,
    sortable: false,
    priority: "secondary",
    render: (batch) => formatImportLastAnalyzedAt(batch.analyzed_at),
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
    priority: "secondary",
    render: (batch) => new Date(batch.created_at).toLocaleString("tr-TR"),
  },
  {
    key: "actions",
    title: dataIntegrationLabels.colActions,
    sortable: false,
    priority: "primary",
    className: "actions",
    render: (batch) => (
      <TableRowActions className="import-list-actions">
        {handlers.canUpdate && canAnalyze(batch.status) && (
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={handlers.analyzingBatchId === batch.id}
            onClick={() => handlers.onAnalyze?.(batch)}
          >
            {handlers.analyzingBatchId === batch.id
              ? dataIntegrationLabels.analyzeBatchRunning
              : dataIntegrationLabels.analyzeBatch}
          </button>
        )}
        {handlers.canUpdate && canReanalyze(batch.status) && (
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={handlers.analyzingBatchId === batch.id}
            onClick={() => handlers.onAnalyze?.(batch, { reanalyze: true })}
          >
            {handlers.analyzingBatchId === batch.id
              ? dataIntegrationLabels.reanalyzeBatchRunning
              : dataIntegrationLabels.reanalyzeBatch}
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
      </TableRowActions>
    ),
  },
];

export function DataIntegrationImportsPage({
  onOpenBatch,
  onContinueBatch,
}: DataIntegrationImportsPageProps) {
  const { can } = usePermissions();
  const canUpdate = can(IMPORT_PERMISSION_UPDATE);
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
    async (batch: ImportBatch, options?: { reanalyze?: boolean }) => {
      if (!canUpdate) return;
      setActionError(null);
      setSuccessMessage(null);
      setAnalyzingBatchId(batch.id);
      try {
        const job = await startImportAnalyzeJob(batch.id);
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          const status = await getImportJob(job.job_id);
          if (status.status === "completed") {
            await table.refresh();
            if (options?.reanalyze) {
              setSuccessMessage(dataIntegrationLabels.reanalyzeBatchSuccess);
            }
            return;
          }
          if (status.status === "failed") {
            throw new ApiError(status.error_message ?? dataIntegrationLabels.analyzeBatchFailed, 500, status);
          }
          await new Promise((r) => window.setTimeout(r, 800));
        }
        throw new ApiError(dataIntegrationLabels.analyzeBatchTimeout, 504);
      } catch (err) {
        setActionError(
          err instanceof ApiError ? err.message : dataIntegrationLabels.analyzeBatchFailed,
        );
        await table.refresh();
      } finally {
        setAnalyzingBatchId(null);
      }
    },
    [canUpdate, table.refresh],
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
        onAnalyze: (batch, options) => void handleAnalyze(batch, options),
        onDelete: setBatchToDelete,
        canUpdate,
        analyzingBatchId,
        deletingBatchId,
      }),
    [canUpdate, handleOpen, handleAnalyze, analyzingBatchId, deletingBatchId],
  );

  return (
    <PageShell>
      <PageHeader title={dataIntegrationLabels.importsTitle} subtitle={dataIntegrationLabels.importsSubtitle} />

      {successMessage && <Banner variant="success" as="p">{successMessage}</Banner>}

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(batch) => batch.id}
        skeletonCols={7}
        emptyState={<EmptyState title={dataIntegrationLabels.importsEmpty} description="" />}
      />
      {(table.error || actionError) && (
        <Banner variant="error" as="p">
          {actionError ?? table.error}
        </Banner>
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
    </PageShell>
  );
}
