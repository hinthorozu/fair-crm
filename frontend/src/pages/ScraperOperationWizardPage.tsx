import React from "react";
import { getFair } from "../api/fairs";
import { createOperation } from "../api/operations";
import { getScraperManifest, listAdapters } from "../api/scraper";
import { ApiError } from "../api/client";
import { FairEntitySelect } from "../components/FairEntitySelect";
import {
  OutputFieldsSection,
  toggleRequestedFieldSelection,
} from "../components/scraper/OutputFieldsSection";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { LoadingState } from "../components/ui/LoadingState";
import {
  FieldError,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextareaInput,
  TextInput,
  clearNavigationDirtySources,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import {
  operationLabels,
  operationTypeLabels,
  wizardStepLabels,
} from "../labels/operationLabels";
import type { Fair } from "../types/fair";
import type { AdapterListItem, RequestedOutputField, ScraperManifest } from "../types/scraper";
import {
  filterRequestedFieldsByCapabilities,
  manifestCapabilities,
  resolveRequestedFieldsForManifest,
} from "../utils/adapterManifestForm";
import { isCustomerContactEnrichmentAdapter } from "../utils/enrichmentAdapter";
import { getOutputFieldLabel } from "../utils/outputFieldDefinitions";
import {
  formatScraperConfigJson,
  parseScraperConfigJson,
} from "../utils/scraperOperationWizard";

interface ScraperOperationWizardPageProps {
  onCancel: () => void;
  onCreated: (operationId: string) => void;
}

type WizardStepId = "fair" | "scraper_info" | "summary";

const STEPS: Array<{ id: WizardStepId; required: boolean }> = [
  { id: "fair", required: true },
  { id: "scraper_info", required: true },
  { id: "summary", required: true },
];

const EMPTY_WIZARD_STATE = {
  selectedFairId: "",
  adapterKey: "",
  sourceUrl: "",
  scraperConfigText: "{\n}",
  title: "",
  requestedFields: [] as RequestedOutputField[],
};

export function ScraperOperationWizardPage({
  onCancel,
  onCreated,
}: ScraperOperationWizardPageProps) {
  return (
    <FormDirtyHost onClose={onCancel}>
      <ScraperOperationWizardPageInner onCancel={onCancel} onCreated={onCreated} />
    </FormDirtyHost>
  );
}

function ScraperOperationWizardPageInner({
  onCancel,
  onCreated,
}: ScraperOperationWizardPageProps) {
  const requestLeave = useModalFormCancel(onCancel);
  const [stepIndex, setStepIndex] = React.useState(0);
  const [fieldError, setFieldError] = React.useState<string | null>(null);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const [selectedFairId, setSelectedFairId] = React.useState("");
  const [fair, setFair] = React.useState<Fair | null>(null);
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);

  const [adapterKey, setAdapterKey] = React.useState("");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [scraperConfigText, setScraperConfigText] = React.useState("{\n}");
  const [title, setTitle] = React.useState("");

  const [manifest, setManifest] = React.useState<ScraperManifest | null>(null);
  const [requestedFields, setRequestedFields] = React.useState<RequestedOutputField[]>([]);

  const [step2Loading, setStep2Loading] = React.useState(false);
  const [step2Error, setStep2Error] = React.useState<string | null>(null);
  const [manifestLoading, setManifestLoading] = React.useState(false);
  const [manifestError, setManifestError] = React.useState<string | null>(null);

  /** Fair id loaded into step 2 — avoids refetch/reset when returning from summary. */
  const loadedFairIdRef = React.useRef<string | null>(null);
  const manifestRequestIdRef = React.useRef(0);

  const wizardValues = React.useMemo(
    () => ({
      selectedFairId,
      adapterKey,
      sourceUrl,
      scraperConfigText,
      title,
      requestedFields,
    }),
    [selectedFairId, adapterKey, sourceUrl, scraperConfigText, title, requestedFields],
  );
  useReportFormDirty(wizardValues, EMPTY_WIZARD_STATE);

  const currentStep = STEPS[stepIndex] ?? STEPS[0];
  const capabilities = React.useMemo(
    () => (manifest ? manifestCapabilities(manifest) : null),
    [manifest],
  );
  const selectedAdapter = adapters.find((item) => item.adapter_key === adapterKey) ?? null;
  const parsedConfig = React.useMemo(
    () => parseScraperConfigJson(scraperConfigText),
    [scraperConfigText],
  );
  const selectedRequestedFields = filterRequestedFieldsByCapabilities(
    requestedFields,
    capabilities,
  );

  const loadManifestForAdapter = React.useCallback(async (nextAdapterKey: string) => {
    const requestId = ++manifestRequestIdRef.current;
    const trimmed = nextAdapterKey.trim();
    if (!trimmed) {
      setManifest(null);
      setManifestError(null);
      setRequestedFields([]);
      setManifestLoading(false);
      return;
    }

    setManifestLoading(true);
    setManifestError(null);
    try {
      const nextManifest = await getScraperManifest(trimmed);
      if (requestId !== manifestRequestIdRef.current) return;
      setManifest(nextManifest);
      // Canonical defaults for supported fields; drops unsupported prior selections.
      setRequestedFields(resolveRequestedFieldsForManifest(nextManifest));
    } catch (err) {
      if (requestId !== manifestRequestIdRef.current) return;
      setManifest(null);
      setRequestedFields([]);
      setManifestError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      if (requestId === manifestRequestIdRef.current) {
        setManifestLoading(false);
      }
    }
  }, []);

  // Step 2 entry only: load fair scraper fields + adapters (+ initial manifest).
  React.useEffect(() => {
    if (currentStep.id !== "scraper_info") return;
    if (!selectedFairId) return;
    if (loadedFairIdRef.current === selectedFairId) return;

    let cancelled = false;
    setStep2Loading(true);
    setStep2Error(null);
    setFieldError(null);

    (async () => {
      try {
        const [nextFair, adaptersResponse] = await Promise.all([
          getFair(selectedFairId),
          listAdapters(),
        ]);
        if (cancelled) return;

        setAdapters(
          adaptersResponse.items.filter(
            (item) => item.is_active && !isCustomerContactEnrichmentAdapter(item.adapter_key),
          ),
        );
        setFair(nextFair);

        const nextAdapter = (nextFair.adapter_key || "").trim();
        setAdapterKey(nextAdapter);
        setSourceUrl((nextFair.source_url || "").trim());
        setScraperConfigText(formatScraperConfigJson(nextFair.scraper_config));
        setTitle(`${nextFair.name} scraper`);
        loadedFairIdRef.current = selectedFairId;

        if (!cancelled) {
          await loadManifestForAdapter(nextAdapter);
        }
      } catch (err) {
        if (!cancelled) {
          setStep2Error(err instanceof ApiError ? err.message : operationLabels.loadError);
          loadedFairIdRef.current = null;
        }
      } finally {
        if (!cancelled) setStep2Loading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [currentStep.id, selectedFairId, loadManifestForAdapter]);

  const canProceed = (() => {
    switch (currentStep.id) {
      case "fair":
        return Boolean(selectedFairId);
      case "scraper_info":
        return (
          !step2Loading &&
          !manifestLoading &&
          Boolean(adapterKey.trim()) &&
          Boolean(sourceUrl.trim()) &&
          parsedConfig.ok &&
          !manifestError &&
          Boolean(manifest) &&
          selectedRequestedFields.length > 0
        );
      case "summary":
        return (
          Boolean(adapterKey.trim()) &&
          Boolean(sourceUrl.trim()) &&
          parsedConfig.ok &&
          selectedRequestedFields.length > 0
        );
      default:
        return false;
    }
  })();

  const validateCurrentStep = (): boolean => {
    if (currentStep.id === "fair") {
      if (!selectedFairId) {
        setFieldError(operationLabels.fairRequired);
        return false;
      }
    }
    if (currentStep.id === "scraper_info") {
      if (step2Loading || manifestLoading) return false;
      if (step2Error) {
        setFieldError(step2Error);
        return false;
      }
      if (!adapterKey.trim()) {
        setFieldError(operationLabels.adapterRequired);
        return false;
      }
      if (!sourceUrl.trim()) {
        setFieldError(operationLabels.fairSourceUrlRequired);
        return false;
      }
      if (!parsedConfig.ok) {
        setFieldError(parsedConfig.error);
        return false;
      }
      if (manifestError) {
        setFieldError(manifestError);
        return false;
      }
      if (!manifest) {
        setFieldError(operationLabels.adapterRequired);
        return false;
      }
      if (selectedRequestedFields.length === 0) {
        setFieldError(operationLabels.requestedFieldsRequired);
        return false;
      }
    }
    setFieldError(null);
    return true;
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    setStepIndex((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const goBack = () => {
    setFieldError(null);
    setStepIndex((prev) => Math.max(prev - 1, 0));
  };

  const buildPayload = () => {
    const config = parsedConfig.ok ? parsedConfig.value : {};
    const typeConfig: Record<string, unknown> = {
      adapter_key: adapterKey.trim(),
      requested_fields: selectedRequestedFields,
      source_url: sourceUrl.trim(),
      scraper_config: config,
    };
    if (typeof config.max_pages === "number" && Number.isFinite(config.max_pages)) {
      typeConfig.max_pages = config.max_pages;
    } else if (typeof config.max_pages === "string" && config.max_pages.trim()) {
      const parsed = Number(config.max_pages);
      if (Number.isFinite(parsed)) typeConfig.max_pages = parsed;
    }
    if (typeof config.use_http === "boolean") {
      typeConfig.use_http = config.use_http;
    }
    if (typeof config.scrape_detail === "boolean") {
      typeConfig.scrape_detail = config.scrape_detail;
    }

    return {
      operation_type: "scraper" as const,
      title: title.trim() || fair?.name || operationTypeLabels.scraper,
      source_kind: "fair" as const,
      source_ids: [selectedFairId],
      type_config: typeConfig,
      start_immediately: true,
    };
  };

  const submit = async () => {
    if (!validateCurrentStep()) return;
    if (!canProceed) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await createOperation(buildPayload());
      clearNavigationDirtySources();
      onCreated(created.id);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageShell className="operation-wizard scraper-operation-wizard">
      <PageHeader
        title={operationLabels.scraperWizardTitle}
        subtitle={operationLabels.scraperWizardSubtitle}
        breadcrumbs={[
          { label: operationLabels.pageTitle, onClick: requestLeave },
          { label: operationLabels.scraperWizardTitle, current: true },
        ]}
      />

      {submitError ? <Banner variant="error">{submitError}</Banner> : null}

      <div className="wizard-stepper" aria-label="Wizard adımları">
        {STEPS.map((step, index) => (
          <span
            key={step.id}
            className={`wizard-step ${
              index === stepIndex ? "active" : index < stepIndex ? "done" : ""
            }`}
          >
            {index + 1}. {wizardStepLabels[step.id] ?? step.id}
          </span>
        ))}
      </div>

      <Card>
        {currentStep.id === "fair" ? (
          <FormField
            label={operationLabels.stepFair}
            htmlFor="scraper-wizard-fair"
            required
            fullWidth
          >
            <FairEntitySelect
              id="scraper-wizard-fair"
              value={selectedFairId}
              onChange={(nextId) => {
                // Step 1: only update selection — no fetch / validation / loading.
                setSelectedFairId(nextId);
                loadedFairIdRef.current = null;
                setFieldError(null);
              }}
              allowClear
            />
          </FormField>
        ) : null}

        {currentStep.id === "scraper_info" ? (
          step2Loading ? (
            <LoadingState />
          ) : (
            <FormGrid>
              {step2Error ? <Banner variant="error">{step2Error}</Banner> : null}
              <FormField
                label={operationLabels.stepAdapter}
                htmlFor="scraper-wizard-adapter"
                required
                fullWidth
              >
                <SelectInput
                  id="scraper-wizard-adapter"
                  value={adapterKey}
                  onChange={(event) => {
                    const next = event.target.value;
                    setAdapterKey(next);
                    setFieldError(null);
                    void loadManifestForAdapter(next);
                  }}
                >
                  <option value="">Seçin…</option>
                  {adapters.map((item) => (
                    <option key={item.adapter_key} value={item.adapter_key}>
                      {item.display_name || item.adapter_key}
                    </option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField
                label={operationLabels.fairSourceUrlLabel}
                htmlFor="scraper-wizard-source-url"
                required
                fullWidth
              >
                <TextInput
                  id="scraper-wizard-source-url"
                  value={sourceUrl}
                  onChange={(event) => {
                    setSourceUrl(event.target.value);
                    setFieldError(null);
                  }}
                />
              </FormField>
              <FormField
                label={operationLabels.fairScraperConfigLabel}
                htmlFor="scraper-wizard-config-json"
                fullWidth
                error={!parsedConfig.ok ? parsedConfig.error : undefined}
              >
                <TextareaInput
                  id="scraper-wizard-config-json"
                  value={scraperConfigText}
                  onChange={(event) => {
                    setScraperConfigText(event.target.value);
                    setFieldError(null);
                  }}
                  rows={8}
                  aria-invalid={!parsedConfig.ok}
                />
              </FormField>

              <div style={{ gridColumn: "1 / -1" }}>
                <FormSection title={operationLabels.stepOutputFields}>
                  {manifestLoading ? <LoadingState variant="inline" /> : null}
                  {manifestError ? <Banner variant="error">{manifestError}</Banner> : null}
                  {!manifestLoading && manifest && capabilities ? (
                    <OutputFieldsSection
                      requestedFields={requestedFields}
                      capabilities={capabilities}
                      onChange={(field, enabled) => {
                        setRequestedFields((current) =>
                          toggleRequestedFieldSelection(current, field, enabled),
                        );
                        setFieldError(null);
                      }}
                    />
                  ) : null}
                </FormSection>
              </div>
              {fieldError ? <FieldError>{fieldError}</FieldError> : null}
            </FormGrid>
          )
        ) : null}

        {currentStep.id === "summary" ? (
          <dl className="detail-grid">
            <div>
              <dt>{operationLabels.stepFair}</dt>
              <dd>{fair?.name || "—"}</dd>
            </div>
            <div>
              <dt>{operationLabels.stepAdapter}</dt>
              <dd>{selectedAdapter?.display_name || adapterKey || "—"}</dd>
            </div>
            <div>
              <dt>{operationLabels.fairSourceUrlLabel}</dt>
              <dd>{sourceUrl.trim() || "—"}</dd>
            </div>
            <div>
              <dt>{operationLabels.fairScraperConfigLabel}</dt>
              <dd>
                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                  {parsedConfig.ok
                    ? JSON.stringify(parsedConfig.value, null, 2)
                    : scraperConfigText}
                </pre>
              </dd>
            </div>
            <div>
              <dt>{operationLabels.stepOutputFields}</dt>
              <dd>
                {selectedRequestedFields.length > 0
                  ? selectedRequestedFields.map((field) => getOutputFieldLabel(field)).join(", ")
                  : "—"}
              </dd>
            </div>
          </dl>
        ) : null}

        <div
          className="wizard-nav"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--space-3)",
            marginTop: "var(--space-5)",
          }}
        >
          <Button type="button" variant="secondary" onClick={requestLeave} disabled={submitting}>
            {operationLabels.dismiss}
          </Button>
          {stepIndex > 0 ? (
            <Button
              type="button"
              variant="secondary"
              onClick={goBack}
              disabled={submitting || step2Loading}
            >
              {operationLabels.back}
            </Button>
          ) : null}
          {stepIndex < STEPS.length - 1 ? (
            <Button
              type="button"
              variant="primary"
              onClick={goNext}
              disabled={submitting || !canProceed || step2Loading || manifestLoading}
            >
              {operationLabels.next}
            </Button>
          ) : (
            <Button
              type="button"
              variant="primary"
              loading={submitting}
              disabled={!canProceed}
              onClick={() => void submit()}
            >
              {operationLabels.startAutomation}
            </Button>
          )}
        </div>
      </Card>
    </PageShell>
  );
}
