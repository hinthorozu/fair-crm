import React from "react";
import {
  getCustomerContactEnrichmentState,
  runCustomerContactEnrichment,
} from "../../api/customers";
import { getScraperRun, listScraperRunLogs, resetEnrichmentState } from "../../api/scraper";
import { ApiError } from "../../api/client";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { ConfirmDialog } from "../ui/ConfirmDialog";
import { LoadingState } from "../ui/LoadingState";
import { customerEnrichmentLabels, customerEnrichmentStatusLabel } from "../../labels/customerEnrichmentLabels";
import { scraperLabels } from "../../labels/scraperLabels";
import type { CustomerContactEnrichmentState } from "../../types/customerEnrichment";
import type { EnrichmentRunSummary, ScraperRunLog } from "../../types/scraper";
import { ENRICHMENT_OUTPUT_FIELD_KEYS } from "../../utils/enrichmentAdapter";
import { formatScraperLogStepLabel } from "../../utils/scraperLogStepLabels";
import { runStatusBadgeVariant, runStatusLabel } from "../../utils/scraperBadges";

const POLL_INTERVAL_MS = 2000;

interface CustomerContactEnrichmentTabProps {
  customerId: string;
  disabled?: boolean;
  onOpenImportBatch?: (batchId: string) => void;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function RunSummary({ summary }: { summary: EnrichmentRunSummary }) {
  return (
    <dl className="detail-grid enrichment-run-summary">
      <dt>{customerEnrichmentLabels.summaryEmailFound}</dt>
      <dd>{summary.emails_found > 0 ? customerEnrichmentLabels.yes : customerEnrichmentLabels.no}</dd>
      <dt>{customerEnrichmentLabels.summaryPhoneFound}</dt>
      <dd>{(summary.phones_found ?? 0) > 0 ? customerEnrichmentLabels.yes : customerEnrichmentLabels.no}</dd>
      <dt>{customerEnrichmentLabels.summaryImportBatch}</dt>
      <dd>
        {summary.import_batch_created
          ? customerEnrichmentLabels.summaryImportCreated
          : customerEnrichmentLabels.summaryImportNone}
      </dd>
    </dl>
  );
}

function LogList({ logs }: { logs: ScraperRunLog[] }) {
  if (logs.length === 0) {
    return <p className="text-muted">{customerEnrichmentLabels.emptyHistory}</p>;
  }
  return (
    <ul className="adapter-run-log-list">
      {logs.map((log) => (
        <li key={log.id} className={`adapter-run-log adapter-run-log-${log.level}`}>
          <span className="adapter-run-log-time">{new Date(log.created_at).toLocaleTimeString("tr-TR")}</span>
          <span className="adapter-run-log-step">{formatScraperLogStepLabel(log.step)}</span>
          <span className="adapter-run-log-message">{log.message}</span>
        </li>
      ))}
    </ul>
  );
}

export function CustomerContactEnrichmentTab({
  customerId,
  disabled = false,
  onOpenImportBatch,
}: CustomerContactEnrichmentTabProps) {
  const [state, setState] = React.useState<CustomerContactEnrichmentState | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);
  const [resetting, setResetting] = React.useState(false);
  const [showResetConfirm, setShowResetConfirm] = React.useState(false);
  const [resetSuccess, setResetSuccess] = React.useState<string | null>(null);
  const [activeRunId, setActiveRunId] = React.useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = React.useState<string | null>(null);
  const [liveLogs, setLiveLogs] = React.useState<ScraperRunLog[]>([]);
  const [runSummary, setRunSummary] = React.useState<EnrichmentRunSummary | null>(null);
  const lastLogIdRef = React.useRef<string | null>(null);

  const loadState = React.useCallback(async () => {
    setError(null);
    try {
      const data = await getCustomerContactEnrichmentState(customerId);
      setState(data);
      return data;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : customerEnrichmentLabels.loadError);
      return null;
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  React.useEffect(() => {
    setLoading(true);
    void loadState();
  }, [loadState]);

  const pollRun = React.useCallback(async (runId: string) => {
    lastLogIdRef.current = null;
    setLiveLogs([]);
    setRunSummary(null);
    setActiveRunId(runId);

    for (let attempt = 0; attempt < 120; attempt += 1) {
      const run = await getScraperRun(runId);
      setActiveRunStatus(run.status);
      if (run.enrichment_summary) {
        setRunSummary(run.enrichment_summary);
      }

      const logResponse = await listScraperRunLogs(runId, {
        after_id: lastLogIdRef.current ?? undefined,
        limit: 500,
      });
      if (logResponse.items.length > 0) {
        lastLogIdRef.current = logResponse.items[logResponse.items.length - 1]?.id ?? lastLogIdRef.current;
        setLiveLogs((current) => [...current, ...logResponse.items]);
      }

      if (run.status === "completed" || run.status === "failed" || run.status === "cancelled") {
        await loadState();
        return run;
      }
      await sleep(POLL_INTERVAL_MS);
    }
    throw new Error(scraperLabels.enrichmentRunTimeout);
  }, [loadState]);

  const handleRun = React.useCallback(async () => {
    if (!state?.can_run) {
      return;
    }
    setRunning(true);
    setError(null);
    setResetSuccess(null);
    setRunSummary(null);
    try {
      const started = await runCustomerContactEnrichment(customerId, {
        dry_run: false,
        requested_fields: [...ENRICHMENT_OUTPUT_FIELD_KEYS],
      });
      await pollRun(started.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : customerEnrichmentLabels.runFailed);
    } finally {
      setRunning(false);
    }
  }, [customerId, pollRun, state?.can_run]);

  const handleReset = React.useCallback(async () => {
    setResetting(true);
    setError(null);
    setResetSuccess(null);
    try {
      await resetEnrichmentState({ customer_ids: [customerId] });
      setResetSuccess(customerEnrichmentLabels.resetSuccess);
      setShowResetConfirm(false);
      setRunSummary(null);
      setActiveRunId(null);
      setLiveLogs([]);
      await loadState();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : customerEnrichmentLabels.resetFailed);
      setShowResetConfirm(false);
    } finally {
      setResetting(false);
    }
  }, [customerId, loadState]);

  if (loading) {
    return <LoadingState />;
  }

  const displayLogs =
    liveLogs.length > 0 ? liveLogs : state?.recent_logs ?? [];
  const importBatchId = runSummary?.import_batch_id ?? state?.import_batch_id ?? null;

  return (
    <div className="customer-contact-enrichment-tab">
      <p className="form-hint">{customerEnrichmentLabels.intro}</p>

      <div className="customer-enrichment-actions">
        <button
          type="button"
          className="btn primary"
          disabled={disabled || running || resetting || !state?.can_run}
          onClick={() => void handleRun()}
        >
          {running ? customerEnrichmentLabels.running : customerEnrichmentLabels.runButton}
        </button>
        <button
          type="button"
          className="btn secondary"
          disabled={disabled || running || resetting}
          onClick={() => setShowResetConfirm(true)}
        >
          {resetting ? customerEnrichmentLabels.resetting : customerEnrichmentLabels.resetButton}
        </button>
      </div>

      {state && !state.can_run && state.block_message ? (
        <p className="banner warning">{state.block_message}</p>
      ) : null}
      {error ? <p className="banner error">{error}</p> : null}
      {resetSuccess ? <p className="import-apply-result-success">{resetSuccess}</p> : null}

      {state ? (
        <Card title={customerEnrichmentLabels.statusTitle}>
          <dl className="detail-grid">
            <dt>{customerEnrichmentLabels.statusTitle}</dt>
            <dd>
              <Badge variant="neutral">{customerEnrichmentStatusLabel(state.status)}</Badge>
            </dd>
            <dt>{customerEnrichmentLabels.lastScan}</dt>
            <dd>{formatDateTime(state.last_email_scan_at)}</dd>
            <dt>{customerEnrichmentLabels.lastRunId}</dt>
            <dd>{state.last_enrichment_run_id ?? "—"}</dd>
            <dt>{customerEnrichmentLabels.lastEmail}</dt>
            <dd>{state.last_email_found ?? "—"}</dd>
            <dt>{customerEnrichmentLabels.sourceUrl}</dt>
            <dd>{state.last_source_url ?? "—"}</dd>
            <dt>{customerEnrichmentLabels.lastError}</dt>
            <dd>{state.last_error ?? "—"}</dd>
            <dt>{customerEnrichmentLabels.retryAfter}</dt>
            <dd>{formatDateTime(state.retry_after)}</dd>
            <dt>{customerEnrichmentLabels.website}</dt>
            <dd>{state.website ?? "—"}</dd>
            <dt>{customerEnrichmentLabels.hasCrmEmail}</dt>
            <dd>{state.has_crm_email ? customerEnrichmentLabels.yes : customerEnrichmentLabels.no}</dd>
            <dt>{customerEnrichmentLabels.importBatch}</dt>
            <dd>
              {importBatchId && onOpenImportBatch ? (
                <button type="button" className="btn link" onClick={() => onOpenImportBatch(importBatchId)}>
                  {customerEnrichmentLabels.openImportBatch}
                </button>
              ) : importBatchId ? (
                importBatchId
              ) : (
                "—"
              )}
            </dd>
          </dl>
        </Card>
      ) : null}

      {activeRunId && activeRunStatus ? (
        <Card title={customerEnrichmentLabels.runSummaryTitle}>
          <p>
            <Badge variant={runStatusBadgeVariant(activeRunStatus)}>
              {runStatusLabel(activeRunStatus)}
            </Badge>
          </p>
          {runSummary ? <RunSummary summary={runSummary} /> : null}
        </Card>
      ) : null}

      <Card title={customerEnrichmentLabels.historyTitle}>
        <LogList logs={displayLogs} />
      </Card>

      {showResetConfirm ? (
        <ConfirmDialog
          title={customerEnrichmentLabels.resetConfirmTitle}
          message={customerEnrichmentLabels.resetConfirmMessage}
          confirmLabel={customerEnrichmentLabels.resetConfirmAction}
          variant="danger"
          loading={resetting}
          onCancel={() => setShowResetConfirm(false)}
          onConfirm={() => void handleReset()}
        />
      ) : null}
    </div>
  );
}
