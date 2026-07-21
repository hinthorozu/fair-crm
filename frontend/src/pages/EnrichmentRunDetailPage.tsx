import React from "react";
import { cancelScraperRun, getScraperRun } from "../api/scraper";
import { ApiError } from "../api/client";
import { AdapterRunLogConsole } from "../components/scraper/AdapterRunLogConsole";
import { EnrichmentRunLogExportMenu } from "../components/scraper/EnrichmentRunLogExportMenu";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { scraperLabels } from "../labels/scraperLabels";
import type { EnrichmentRunSummary, ScraperRun } from "../types/scraper";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "../utils/enrichmentAdapter";
import { isActiveScraperRunStatus, runStatusBadgeVariant, runStatusLabel } from "../utils/scraperBadges";

const POLL_INTERVAL_MS = 2000;

interface EnrichmentRunDetailPageProps {
  runId: string;
  adapterKey?: string;
  onBack: () => void;
  onOpenImportBatch?: (batchId: string) => void;
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

export function EnrichmentRunDetailPage({
  runId,
  adapterKey: adapterKeyProp,
  onBack,
  onOpenImportBatch,
}: EnrichmentRunDetailPageProps) {
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
  }, [runId, loadRun]);

  const showCancelButton = run?.status === "running";
  const showCancellingState =
    run?.status === "cancel_requested" || run?.status === "cancelling";

  if (loading && !run) {
    return <LoadingState />;
  }

  const adapterKey = adapterKeyProp ?? run?.adapter_key ?? CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY;
  const summary = run?.enrichment_summary ?? null;

  return (
    <div className="page enrichment-run-detail-page">
      <PageHeader
        title={scraperLabels.enrichmentRunDetailTitle}
        subtitle={scraperLabels.enrichmentRunDetailSubtitle}
        actions={
          <>
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
            <button type="button" className="btn secondary" onClick={onBack}>
              {scraperLabels.enrichmentRunDetailBackEnrichment}
            </button>
          </>
        }
      />

      {error ? <div className="banner error">{error}</div> : null}
      {cancelError ? <div className="banner error">{cancelError}</div> : null}
      {showCancellingState ? (
        <div className="banner info">{scraperLabels.runStatusCancelRequested}</div>
      ) : null}

      <Card>
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
      </Card>

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
