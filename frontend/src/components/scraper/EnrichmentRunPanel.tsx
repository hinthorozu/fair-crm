import React from "react";
import { getFair, runFairContactEnrichment } from "../../api/fairs";
import { getScraperRun, runCustomerContactEnrichment } from "../../api/scraper";
import { FairEntitySelect } from "../FairEntitySelect";
import { NavIconClose } from "../layout/NavIcons";
import { IconButton } from "../ui/IconButton";
import { CheckboxField, FormField, FormGrid, RadioField, TextInput } from "../ui/form";
import { scraperLabels } from "../../labels/scraperLabels";
import type {
  CompanyNameMatchMode,
  EnrichmentRunPayload,
  EnrichmentRunSummary,
  RequestedOutputField,
  ScraperManifest,
  ScraperRun,
} from "../../types/scraper";
import { manifestCapabilities, resolveRequestedFieldsForManifest } from "../../utils/adapterManifestForm";
import {
  ENRICHMENT_OUTPUT_FIELD_KEYS,
  filterEnrichmentRequestedFields,
} from "../../utils/enrichmentAdapter";
import { OutputFieldsSection, toggleRequestedFieldSelection } from "./OutputFieldsSection";
import { EnrichmentStateResetPanel } from "./EnrichmentStateResetPanel";

type SelectedFair = { id: string; name: string };

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
  /**
   * When set, called instead of the direct enrichment-run API (Operations path).
   * Return value is passed to onRunStarted (typically operation_id).
   */
  startVia?: (payload: EnrichmentRunPayload) => Promise<string>;
}

const POLL_INTERVAL_MS = 2000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function optionalTrimmed(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

export function EnrichmentRunPanel({
  adapterKey,
  manifest,
  fairId,
  onRunFinished,
  onOpenRunDetail,
  onRunStarted,
  startVia,
}: EnrichmentRunPanelProps) {
  /** Empty string = no limit (all eligible customers); the "50" shown to the user is only a placeholder hint. */
  const [limitInput, setLimitInput] = React.useState("");
  const [includeExistingEmail, setIncludeExistingEmail] = React.useState(false);
  const [fairPickerId, setFairPickerId] = React.useState("");
  const [selectedFairs, setSelectedFairs] = React.useState<SelectedFair[]>([]);
  const [fairAddError, setFairAddError] = React.useState<string | null>(null);
  const [companyName, setCompanyName] = React.useState("");
  const [companyNameMatch, setCompanyNameMatch] = React.useState<CompanyNameMatchMode>("contains");
  const [addressContains, setAddressContains] = React.useState("");
  const [requestedFields, setRequestedFields] = React.useState<RequestedOutputField[]>(() =>
    filterEnrichmentRequestedFields(resolveRequestedFieldsForManifest(manifest)),
  );
  const [running, setRunning] = React.useState(false);
  const [redirecting, setRedirecting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [activeRun, setActiveRun] = React.useState<ScraperRun | null>(null);
  const [summary, setSummary] = React.useState<EnrichmentRunSummary | null>(null);

  const fairScoped = Boolean(fairId);
  const selectedFairIds = selectedFairs.map((fair) => fair.id);

  const handleFairPickerChange = React.useCallback((nextId: string) => {
    setFairPickerId(nextId);
    setFairAddError(null);
    if (!nextId) return;

    if (selectedFairs.some((fair) => fair.id === nextId)) {
      setFairAddError(scraperLabels.enrichmentRunFairAlreadySelected);
      setFairPickerId("");
      return;
    }

    void getFair(nextId)
      .then((fair) => {
        setSelectedFairs((current) => {
          if (current.some((item) => item.id === fair.id)) return current;
          return [...current, { id: fair.id, name: fair.name }];
        });
        setFairPickerId("");
      })
      .catch(() => {
        setFairPickerId("");
      });
  }, [selectedFairs]);

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
      const payload: EnrichmentRunPayload = {
        limit,
        requested_fields: requestedFields,
        include_existing_email: includeExistingEmail,
        company_name: optionalTrimmed(companyName),
        company_name_match: companyNameMatch,
        address_contains: optionalTrimmed(addressContains),
      };

      if (startVia) {
        const startedId = await startVia({
          ...payload,
          fair_ids: selectedFairIds,
          fair_id: selectedFairIds.length === 1 ? selectedFairIds[0] : null,
        });
        if (!startedId) {
          throw new Error(scraperLabels.enrichmentRunMissingId);
        }
        if (onRunStarted) {
          setRedirecting(true);
          onRunStarted(startedId);
          return;
        }
        onRunFinished?.();
        return;
      }

      // Fair-detail page uses the fair-scoped endpoint (ignores prior scan state).
      // Org-wide panel with optional fair filters stays on the org endpoint and passes fair_ids.
      const started = fairScoped && fairId
        ? await runFairContactEnrichment(fairId, payload)
        : await runCustomerContactEnrichment(adapterKey, {
            ...payload,
            fair_id: selectedFairIds.length === 1 ? selectedFairIds[0] : null,
            fair_ids: selectedFairIds.length > 0 ? selectedFairIds : null,
          });
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
  }, [
    adapterKey,
    addressContains,
    companyName,
    companyNameMatch,
    fairId,
    fairScoped,
    includeExistingEmail,
    limitInput,
    onRunFinished,
    onRunStarted,
    pollRun,
    requestedFields,
    selectedFairs,
    startVia,
  ]);

  return (
    <div className="enrichment-run-panel">
      <p className="form-hint">{scraperLabels.enrichmentRunHint}</p>
      <p className="form-hint">{scraperLabels.enrichmentRunFiltersHint}</p>

      <FormGrid columns={3}>
        {!fairScoped ? (
          <>
            <FormField
              label={scraperLabels.enrichmentRunFairSelectLabel}
              htmlFor="enrichment-fair-picker"
              fullWidth
              hint={scraperLabels.enrichmentRunFairFilterHint}
              error={fairAddError ?? undefined}
            >
              <FairEntitySelect
                id="enrichment-fair-picker"
                value={fairPickerId}
                onChange={handleFairPickerChange}
                disabled={running}
                allowClear
                placeholder={scraperLabels.enrichmentRunFairFilterPlaceholder}
              />
            </FormField>

            <FormField label={scraperLabels.enrichmentRunFairSelectedLabel} fullWidth>
              {selectedFairs.length === 0 ? (
                <p className="field-hint">{scraperLabels.enrichmentRunFairSelectedEmpty}</p>
              ) : (
                <ul className="selected-entity-list">
                  {selectedFairs.map((fair) => (
                    <li key={fair.id} className="selected-entity-item">
                      <span>{fair.name}</span>
                      <IconButton
                        label={scraperLabels.enrichmentRunFairRemove}
                        icon={<NavIconClose />}
                        onClick={() => {
                          if (running) return;
                          setSelectedFairs((current) =>
                            current.filter((item) => item.id !== fair.id),
                          );
                          setFairAddError(null);
                        }}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </FormField>
          </>
        ) : null}

        <FormField
          label={scraperLabels.enrichmentRunCompanyName}
          htmlFor="enrichment-company-name"
          hint={scraperLabels.enrichmentRunCompanyNameHint}
        >
          <TextInput
            id="enrichment-company-name"
            type="text"
            value={companyName}
            disabled={running}
            placeholder="SDK"
            onChange={(event) => setCompanyName(event.target.value)}
          />
        </FormField>

        <div className="field">
          <span className="field-label">{scraperLabels.enrichmentRunCompanyNameMatch}</span>
          <div className="radio-group radio-group-horizontal">
            <RadioField
              id="enrichment-match-contains"
              name="enrichment-company-match"
              label={scraperLabels.enrichmentRunCompanyNameMatchContains}
              value="contains"
              checked={companyNameMatch === "contains"}
              disabled={running || !companyName.trim()}
              onChange={(value) => setCompanyNameMatch(value as CompanyNameMatchMode)}
            />
            <RadioField
              id="enrichment-match-starts"
              name="enrichment-company-match"
              label={scraperLabels.enrichmentRunCompanyNameMatchStartsWith}
              value="starts_with"
              checked={companyNameMatch === "starts_with"}
              disabled={running || !companyName.trim()}
              onChange={(value) => setCompanyNameMatch(value as CompanyNameMatchMode)}
            />
          </div>
        </div>

        <FormField
          label={scraperLabels.enrichmentRunAddress}
          htmlFor="enrichment-address"
          hint={scraperLabels.enrichmentRunAddressHint}
        >
          <TextInput
            id="enrichment-address"
            type="text"
            value={addressContains}
            disabled={running}
            placeholder="İstanbul"
            onChange={(event) => setAddressContains(event.target.value)}
          />
        </FormField>

        <FormField
          label={scraperLabels.enrichmentRunLimit}
          htmlFor="enrichment-limit"
          hint={scraperLabels.enrichmentRunLimitHint}
        >
          <TextInput
            id="enrichment-limit"
            type="number"
            min={1}
            max={500}
            placeholder="50"
            value={limitInput}
            disabled={running}
            onChange={(event) => setLimitInput(event.target.value)}
          />
        </FormField>

        <div className="field full-width">
          <span className="field-label">{scraperLabels.manifestOutputFields}</span>
          <OutputFieldsSection
            requestedFields={requestedFields}
            capabilities={capabilities}
            onChange={toggleField}
          />
        </div>

        <CheckboxField
          id="enrichment-include-existing-email"
          label={scraperLabels.enrichmentRunIncludeExistingEmail}
          checked={includeExistingEmail}
          disabled={running}
          onChange={setIncludeExistingEmail}
          hint={scraperLabels.enrichmentRunIncludeExistingEmailHint}
        />
      </FormGrid>

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
