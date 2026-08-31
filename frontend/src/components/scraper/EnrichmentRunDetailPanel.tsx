import React from "react";
import { cancelScraperRun, getScraperRun } from "../../api/scraper";
import { ApiError } from "../../api/client";
import { AdapterRunLogConsole } from "./AdapterRunLogConsole";
import { EnrichmentRunLogExportMenu } from "./EnrichmentRunLogExportMenu";
import { Badge } from "../ui/Badge";
import { ConfirmDialog } from "../ui/ConfirmDialog";
import { LoadingState } from "../ui/LoadingState";
import { scraperLabels } from "../../labels/scraperLabels";
import { usePermissions } from "../../hooks/usePermissions";
import { SCRAPER_PERMISSION_EXECUTE } from "../../permissions/scraperPermissions";
import type { EnrichmentRunSummary, ScraperRun } from "../../types/scraper";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "../../utils/enrichmentAdapter";
import { isActiveScraperRunStatus, runStatusBadgeVariant, runStatusLabel } from "../../utils/scraperBadges";
import { Banner } from "../ui/Banner";

const POLL_INTERVAL_MS = 2000;

export interface EnrichmentRunDetailPanelProps {
  runId: string;
  adapterKey?: string;
  onOpenImportBatch?: (batchId: string) => void;
  /** When false, hide cancel + export chrome (e.g. Operation Detail owns actions). */
  showActions?: boolean;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function EnrichmentSummaryGrid({ summary }: { summary: EnrichmentRunSummary }) {
  return (
    <dl className="detail-grid enrichment-run-summary">
      <dt>{scraperLabels.enrichmentSummaryScanned}</dt>
      <dd>{summary.customers_scanned.toLocaleString("tr-TR")}</dd>
      <dt>{scraperLabels.enrichmentSummaryEmailsFound}</dt>
      <dd>{summary.emails_found.toLocaleString("tr-TR")}</dd>
      <dt>{scraperLabels.enrichmentSummaryNotFound}</dt>
      <dd>{summary.not_found.toLocaleString("tr-TR")}</dd>
      <dt>{scraperLabels.enrichmentSummaryFailed}</dt>
      <dd>{summary.failed.toLocaleString("tr-TR")}</dd>
      <dt>{scraperLabels.enrichmentSummaryImportBatch}</dt>
      <dd>
        {summary.import_batch_created
          ? scraperLabels.enrichmentSummaryImportBatchCreated
          : summary.dry_run
            ? scraperLabels.enrichmentSummaryImportBatchDryRun
            : scraperLabels.enrichmentSummaryImportBatchNone}
      </dd>
      {summary.import_batch_created ? (
        <>
          <dt>{scraperLabels.enrichmentSummaryPendingDecision}</dt>
          <dd>{summary.import_rows.toLocaleString("tr-TR")}</dd>
        </>
      ) : null}
    </dl>
  );
}

/**
 * Shared enrichment run detail body (status, counters, import preview, live logs).
 * Used by /data-integration/runs/:id and Operation Detail for enrichment ops.
 */
export function EnrichmentRunDetailPanel({
  runId,
  adapterKey: adapterKeyProp,
  onOpenImportBatch,
  showActions = true,
}: EnrichmentRunDetailPanelProps) {
  const { can } = usePermissions();
  const canExecute = can(SCRAPER_PERMISSION_EXECUTE);
  const [run, setRun] = React.useState<ScraperRun | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [cancelConfirmOpen, setCancelConfirmOpen] = React.useState(false);
  const [cancelling, setCancelling] = React.useState(false);
  const [cancelError, setCancelError] = React.useState<string | null>(null);

  const loadRun = React.useCallback(async () => {
    try {
      const data = await getScraperRun(runId);
      setRun(data);
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : scraperLabels.loadError);
      return null;
    } finally {
      setLoading(false);
    }
  }, [runId]);

  React.useEffect(() => {
    setLoading(true);
    void loadRun();
  }, [loadRun]);

  React.useEffect(() => {
    if (!run || !isActiveScraperRunStatus(run.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadRun();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [run, loadRun]);

  React.useEffect(() => {
    if (!run || run.status !== "completed") {
      return;
    }
    void loadRun();
  }, [run?.status, loadRun]);

  const handleCancelConfirm = React.useCallback(async () => {
    if (!canExecute) return;
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelScraperRun(runId);
      setCancelConfirmOpen(false);
      await loadRun();
    } catch (err) {
      setCancelError(err instanceof ApiError ? err.message : scraperLabels.enrichmentRunCancelFailed);
    } finally {
      setCancelling(false);
    }
  }, [canExecute, runId, loadRun]);

  const showCancelButton = showActions && canExecute && run?.status === "running";
  const showCancellingState =
    run?.status === "cancel_requested" || run?.status === "cancelling";

  if (loading && !run) {
    return <LoadingState />;
  }

  const adapterKey = adapterKeyProp ?? run?.adapter_key ?? CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY;
  const summary = run?.enrichment_summary ?? null;

  return (
    <div className="enrichment-run-detail-panel">
      {showActions ? (
        <div className="row gap-sm enrichment-run-detail-actions" style={{ marginBottom: 12 }}>
          {run ? <EnrichmentRunLogExportMenu runId={runId} /> : null}
          {showCancelButton ? (
            <button
              type="button"
              className="btn danger"
              onClick={() => setCancelConfirmOpen(true)}
            >
              {scraperLabels.enrichmentRunCancel}
            </button>
          ) : null}
        </div>
      ) : null}

      {error ? <Banner variant="error">{error}</Banner> : null}
      {cancelError ? <Banner variant="error">{cancelError}</Banner> : null}
      {showCancellingState ? (
        <Banner variant="info">{scraperLabels.runStatusCancelRequested}</Banner>
      ) : null}

      <div className="enrichment-run-detail-meta">
        <div className="enrichment-run-detail-status">
          <span className="text-muted">{scraperLabels.enrichmentRunStatus}:</span>
          {run ? (
            <Badge variant={runStatusBadgeVariant(run.status)}>{runStatusLabel(run.status)}</Badge>
          ) : (
            "—"
          )}
        </div>
        {run ? (
          <p className="text-muted enrichment-run-detail-started">
            {formatDateTime(run.started_at)}
            {run.finished_at ? ` — ${formatDateTime(run.finished_at)}` : ""}
          </p>
        ) : null}
        {run?.error_message ? <p className="text-danger">{run.error_message}</p> : null}
      </div>

      {summary ? <EnrichmentSummaryGrid summary={summary} /> : null}

      {summary?.import_batch_id ? (
        <p className="enrichment-run-detail-import-link">
          {onOpenImportBatch ? (
            <button
              type="button"
              className="btn primary"
              onClick={() => onOpenImportBatch(summary.import_batch_id!)}
            >
              {scraperLabels.enrichmentOpenImportBatch}
            </button>
          ) : (
            <a href={`/data-integration/imports/continue/${summary.import_batch_id}`}>
              {scraperLabels.enrichmentOpenImportBatch}
            </a>
          )}
        </p>
      ) : null}

      <AdapterRunLogConsole
        key={runId}
        adapterKey={adapterKey}
        focusRunId={runId}
        hideRunForm
        enrichmentMode
      />

      {cancelConfirmOpen ? (
        <ConfirmDialog
          title={scraperLabels.enrichmentRunCancelConfirmTitle}
          message={scraperLabels.enrichmentRunCancelConfirmMessage}
          confirmLabel={scraperLabels.enrichmentRunCancel}
          variant="danger"
          loading={cancelling}
          onConfirm={() => void handleCancelConfirm()}
          onCancel={() => setCancelConfirmOpen(false)}
        />
      ) : null}
    </div>
  );
}
