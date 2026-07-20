import React from "react";
import { runFairContactEnrichment } from "../../api/fairs";
import { getScraperRun, runCustomerContactEnrichment } from "../../api/scraper";
import { scraperLabels } from "../../labels/scraperLabels";
import type { EnrichmentRunSummary, RequestedOutputField, ScraperManifest, ScraperRun } from "../../types/scraper";
import { manifestCapabilities, resolveRequestedFieldsForManifest } from "../../utils/adapterManifestForm";
import {
  ENRICHMENT_OUTPUT_FIELD_KEYS,
  filterEnrichmentRequestedFields,
} from "../../utils/enrichmentAdapter";
import { OutputFieldsSection, toggleRequestedFieldSelection } from "./OutputFieldsSection";
import { EnrichmentStateResetPanel } from "./EnrichmentStateResetPanel";

interface EnrichmentRunPanelProps {
  adapterKey: string;
  manifest: ScraperManifest;
  /** When set, scopes the run to a single fair's participants instead of the org-wide candidate pool. */
  fairId?: string;
  onRunFinished?: () => void;
  onOpenRunDetail?: (adapterKey: string, runId: string) => void;
  /** When set, called immediately after the run starts (instead of polling in-place) so the
   * caller can navigate straight to the run detail + live log screen. */
  onRunStarted?: (runId: string) => void;
}

const POLL_INTERVAL_MS = 2000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function EnrichmentRunPanel({
  adapterKey,
  manifest,
  fairId,
  onRunFinished,
  onOpenRunDetail,
  onRunStarted,
}: EnrichmentRunPanelProps) {
  /** Empty string = no limit (all eligible customers); the "50" shown to the user is only a placeholder hint. */
  const [limitInput, setLimitInput] = React.useState("");
  const [dryRun, setDryRun] = React.useState(false);
  const [requestedFields, setRequestedFields] = React.useState<RequestedOutputField[]>(() =>
    filterEnrichmentRequestedFields(resolveRequestedFieldsForManifest(manifest)),
  );
  const [running, setRunning] = React.useState(false);
  const [redirecting, setRedirecting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [activeRun, setActiveRun] = React.useState<ScraperRun | null>(null);
  const [summary, setSummary] = React.useState<EnrichmentRunSummary | null>(null);

  const capabilities = React.useMemo(() => {
    const all = manifestCapabilities(manifest);
    return Object.fromEntries(
      ENRICHMENT_OUTPUT_FIELD_KEYS.map((key) => [key, all[key]]),
    ) as Record<RequestedOutputField, boolean>;
  }, [manifest]);

  const toggleField = React.useCallback((field: RequestedOutputField, enabled: boolean) => {
    setRequestedFields((current) =>
      filterEnrichmentRequestedFields(toggleRequestedFieldSelection(current, field, enabled)),
    );
  }, []);

  const pollRun = React.useCallback(async (runId: string) => {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const run = await getScraperRun(runId);
      setActiveRun(run);
      if (run.enrichment_summary) {
        setSummary(run.enrichment_summary);
      }
      if (run.status === "completed" || run.status === "failed" || run.status === "cancelled") {
        return run;
      }
      await sleep(POLL_INTERVAL_MS);
    }
    throw new Error(scraperLabels.enrichmentRunTimeout);
  }, []);

  const handleRun = React.useCallback(async () => {
    const trimmedLimit = limitInput.trim();
    let limit: number | null = null;
    if (trimmedLimit !== "") {
      const parsed = Number(trimmedLimit);
      if (!Number.isInteger(parsed) || parsed < 1 || parsed > 500) {
        setError(scraperLabels.enrichmentRunLimitInvalid);
        return;
      }
      limit = parsed;
    }

    setRunning(true);
    setError(null);
    setSummary(null);
    setActiveRun(null);
    try {
      const payload = {
        limit,
        dry_run: dryRun,
        requested_fields: requestedFields,
      };
      const started = fairId
        ? await runFairContactEnrichment(fairId, payload)
        : await runCustomerContactEnrichment(adapterKey, payload);
      if (!started?.id) {
        // The run may genuinely have been created server-side, but without an id we cannot
        // navigate anywhere useful — surface this explicitly instead of closing silently.
        throw new Error(scraperLabels.enrichmentRunMissingId);
      }
      setActiveRun(started);
      if (onRunStarted) {
        setRedirecting(true);
        onRunStarted(started.id);
        return;
      }
      const finished = await pollRun(started.id);
      if (finished.enrichment_summary) {
        setSummary(finished.enrichment_summary);
      }
      if (finished.status === "failed") {
        setError(finished.error_message ?? scraperLabels.enrichmentRunFailed);
      }
      onRunFinished?.();
    } catch (err) {
      setRedirecting(false);
      setError(err instanceof Error ? err.message : scraperLabels.enrichmentRunFailed);
    } finally {
      setRunning(false);
    }
  }, [adapterKey, dryRun, fairId, limitInput, onRunFinished, onRunStarted, pollRun, requestedFields]);

  return (
    <div className="enrichment-run-panel">
      <p className="form-hint">{scraperLabels.enrichmentRunHint}</p>

      <label className="form-field">
        <span>{scraperLabels.enrichmentRunLimit}</span>
        <input
          type="number"
          min={1}
          max={500}
          placeholder="50"
          value={limitInput}
          disabled={running}
          onChange={(event) => setLimitInput(event.target.value)}
        />
        <span className="form-hint">{scraperLabels.enrichmentRunLimitHint}</span>
      </label>

      <div className="form-field">
        <span>{scraperLabels.manifestOutputFields}</span>
        <OutputFieldsSection
          requestedFields={requestedFields}
          capabilities={capabilities}
          onChange={toggleField}
        />
      </div>

      <label className="output-field-label">
        <input
          type="checkbox"
          checked={dryRun}
          disabled={running}
          onChange={(event) => setDryRun(event.target.checked)}
        />{" "}
        {scraperLabels.enrichmentRunDryRun}
      </label>

      <div className="enrichment-run-actions">
        <button type="button" className="btn primary" disabled={running} onClick={() => void handleRun()}>
          {running
            ? redirecting
              ? scraperLabels.enrichmentRunRedirecting
              : scraperLabels.enrichmentRunRunning
            : scraperLabels.enrichmentRunStart}
        </button>
      </div>

      {error ? <p className="text-danger">{error}</p> : null}

      {activeRun ? (
        <div className="enrichment-run-active-meta">
          <p className="text-muted">
            {scraperLabels.enrichmentRunStatus}: {activeRun.status}
          </p>
          {onOpenRunDetail ? (
            <button
              type="button"
              className="btn link"
              onClick={() => onOpenRunDetail(adapterKey, activeRun.id)}
            >
              {scraperLabels.actionDetail}
            </button>
          ) : null}
        </div>
      ) : null}

      {summary ? (
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
          {summary.import_batch_id ? (
            <>
              <dt>{scraperLabels.runColImportBatch}</dt>
              <dd>
                <a href={`/data-integration/imports/continue/${summary.import_batch_id}`}>
                  {scraperLabels.enrichmentOpenImportBatch}
                </a>
              </dd>
            </>
          ) : null}
        </dl>
      ) : null}

      {fairId ? null : (
        <>
          <hr className="enrichment-panel-divider" />
          <EnrichmentStateResetPanel />
        </>
      )}
    </div>
  );
}
