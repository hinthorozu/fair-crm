import React from "react";
import { createOperation, getOperationWizardMetadata } from "../api/operations";
import { ApiError } from "../api/client";
import { FairSourcePicker } from "../components/operations/FairSourcePicker";
import { Banner } from "../components/ui/Banner";
import { Card } from "../components/ui/Card";
import { LoadingState } from "../components/ui/LoadingState";
import {
  CheckboxField,
  FieldError,
  FormField,
  FormGrid,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import {
  operationLabels,
  operationPriorityLabels,
  operationTypeDescriptions,
  operationTypeLabels,
  sourceKindLabels,
  wizardStepLabels,
} from "../labels/operationLabels";
import type {
  OperationPriority,
  OperationType,
  OperationTypeMetadata,
  SourceKind,
  WizardMetadata,
  WizardStepMeta,
} from "../types/operation";

interface OperationWizardPageProps {
  onCancel: () => void;
  onCreated: (operationId: string) => void;
}

interface WizardFormState {
  operationType: OperationType | "";
  sourceKind: SourceKind | "";
  sourceIds: string[];
  title: string;
  description: string;
  customerId: string;
  dueAt: string;
  assignedUserId: string;
  priority: OperationPriority;
  reminderAt: string;
  note: string;
  retryEnabled: boolean;
  rateLimit: string;
  concurrency: string;
  schedule: string;
  startImmediately: boolean;
}

const INITIAL_FORM: WizardFormState = {
  operationType: "",
  sourceKind: "",
  sourceIds: [],
  title: "",
  description: "",
  customerId: "",
  dueAt: "",
  assignedUserId: "",
  priority: "normal",
  reminderAt: "",
  note: "",
  retryEnabled: false,
  rateLimit: "",
  concurrency: "",
  schedule: "",
  startImmediately: false,
};

function sortSteps(steps: WizardStepMeta[]): WizardStepMeta[] {
  return [...steps].sort((a, b) => a.order - b.order);
}

function resolveVisibleSteps(meta: OperationTypeMetadata | null): WizardStepMeta[] {
  if (!meta) {
    return [
      { id: "type", required: true, order: 1 },
      { id: "summary", required: true, order: 6 },
      { id: "confirm", required: true, order: 7 },
    ];
  }
  return sortSteps(meta.wizard_steps).filter((step) => {
    if (step.id === "source" && meta.supported_sources.length === 1 && meta.supported_sources[0] === "none") {
      return false;
    }
    if (step.id === "scope" && !meta.capabilities.supports_items) {
      return step.required;
    }
    if (step.id === "run_settings") {
      const fields = (meta.run_settings_schema.fields as string[] | undefined) ?? [];
      return fields.length > 0;
    }
    return true;
  });
}

export function OperationWizardPage({ onCancel, onCreated }: OperationWizardPageProps) {
  const [metadata, setMetadata] = React.useState<WizardMetadata | null>(null);
  const [loadingMeta, setLoadingMeta] = React.useState(true);
  const [metaError, setMetaError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<WizardFormState>(INITIAL_FORM);
  const [stepIndex, setStepIndex] = React.useState(0);
  const [fieldError, setFieldError] = React.useState<string | null>(null);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingMeta(true);
      setMetaError(null);
      try {
        const data = await getOperationWizardMetadata();
        if (!cancelled) setMetadata(data);
      } catch (err) {
        if (!cancelled) {
          setMetaError(err instanceof ApiError ? err.message : operationLabels.loadError);
        }
      } finally {
        if (!cancelled) setLoadingMeta(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedType =
    metadata?.types.find((item) => item.type === form.operationType) ?? null;
  const steps = React.useMemo(() => resolveVisibleSteps(selectedType), [selectedType]);
  const currentStep = steps[stepIndex] ?? steps[0];

  React.useEffect(() => {
    setStepIndex(0);
  }, [form.operationType]);

  React.useEffect(() => {
    if (!selectedType) return;
    if (!form.sourceKind || !selectedType.supported_sources.includes(form.sourceKind as SourceKind)) {
      setForm((prev) => ({
        ...prev,
        sourceKind: selectedType.default_source as SourceKind,
        sourceIds: selectedType.default_source === "fair" ? prev.sourceIds : [],
      }));
    }
  }, [selectedType, form.sourceKind]);

  const update = <K extends keyof WizardFormState>(key: K, value: WizardFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldError(null);
  };

  const validateCurrentStep = (): boolean => {
    if (!currentStep) return false;
    if (currentStep.id === "type" && !form.operationType) {
      setFieldError(operationLabels.typeRequired);
      return false;
    }
    if (currentStep.id === "type_config") {
      if (!form.title.trim()) {
        setFieldError(operationLabels.titleRequired);
        return false;
      }
      if (
        form.operationType === "manual_task" &&
        form.sourceKind === "customer" &&
        !form.customerId.trim()
      ) {
        setFieldError("Müşteri kimliği zorunludur.");
        return false;
      }
    }
    if (currentStep.id === "source" && selectedType && !form.sourceKind) {
      setFieldError("Kaynak seçin.");
      return false;
    }
    if (currentStep.id === "source" && form.sourceKind === "fair" && form.sourceIds.length === 0) {
      setFieldError(operationLabels.fairSourceRequired);
      return false;
    }
    return true;
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    setStepIndex((prev) => Math.min(prev + 1, steps.length - 1));
  };

  const goBack = () => {
    setFieldError(null);
    setStepIndex((prev) => Math.max(prev - 1, 0));
  };

  const buildPayload = (startImmediately: boolean) => {
    const typeConfig: Record<string, unknown> = {};
    const sourceConfig: Record<string, unknown> = {};
    const runSettings: Record<string, unknown> = {};

    if (form.operationType === "manual_task") {
      typeConfig.title = form.title.trim();
      typeConfig.description = form.note.trim() || form.description.trim() || null;
      typeConfig.customer_id = form.customerId.trim() || null;
      typeConfig.due_at = form.dueAt ? new Date(form.dueAt).toISOString() : null;
      typeConfig.assigned_user_id = form.assignedUserId.trim() || null;
      typeConfig.assignee_user_id = form.assignedUserId.trim() || null;
      typeConfig.priority = form.priority;
      if (form.customerId.trim()) {
        sourceConfig.customer_id = form.customerId.trim();
      }
    } else {
      typeConfig.note = form.note.trim() || null;
    }

    if (form.retryEnabled) runSettings.retry = true;
    if (form.rateLimit.trim()) runSettings.rate_limit = Number(form.rateLimit);
    if (form.concurrency.trim()) runSettings.concurrency = Number(form.concurrency);
    if (form.schedule.trim()) runSettings.schedule = form.schedule.trim();
    runSettings.priority = form.priority;

    return {
      operation_type: form.operationType as OperationType,
      title: form.title.trim(),
      description: form.description.trim() || null,
      source_kind: (form.sourceKind || "none") as SourceKind,
      source_ids: form.sourceKind === "fair" ? form.sourceIds : [],
      source_config: sourceConfig,
      type_config: typeConfig,
      run_settings: runSettings,
      priority: form.priority,
      start_immediately: startImmediately,
    };
  };

  const submit = async (startImmediately: boolean) => {
    if (!validateCurrentStep()) return;
    if (!form.operationType) {
      setFieldError(operationLabels.typeRequired);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await createOperation(buildPayload(startImmediately));
      onCreated(created.id);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingMeta) {
    return (
      <PageShell>
        <LoadingState />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title={operationLabels.wizardTitle}
        subtitle={operationLabels.wizardSubtitle}
        breadcrumbs={[
          { label: operationLabels.pageTitle, onClick: onCancel },
          { label: operationLabels.wizardTitle, current: true },
        ]}
      />

      {metaError ? <Banner variant="error">{metaError}</Banner> : null}
      {submitError ? <Banner variant="error">{submitError}</Banner> : null}

      <Card>
        <ol className="wizard-steps" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", listStyle: "none", padding: 0 }}>
          {steps.map((step, index) => (
            <li key={step.id}>
              <span className={index === stepIndex ? "badge badge-primary" : "badge badge-neutral"}>
                {index + 1}. {wizardStepLabels[step.id] ?? step.id}
              </span>
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        {currentStep?.id === "type" ? (
          <FormGrid>
            <FormField label={operationLabels.stepType} required>
              <SelectInput
                value={form.operationType}
                onChange={(e) => update("operationType", e.target.value as OperationType | "")}
              >
                <option value="">Seçin…</option>
                {(metadata?.types ?? []).map((item) => (
                  <option key={item.type} value={item.type}>
                    {operationTypeLabels[item.type as OperationType] ?? item.type}
                    {!item.execution_ready ? " (yakında)" : ""}
                  </option>
                ))}
              </SelectInput>
              {fieldError ? <FieldError>{fieldError}</FieldError> : null}
            </FormField>
            {form.operationType ? (
              <p className="text-muted">
                {operationTypeDescriptions[form.operationType as OperationType] ?? ""}
              </p>
            ) : null}
            {selectedType && !selectedType.execution_ready ? (
              <Banner variant="info">{operationLabels.notExecutionReady}</Banner>
            ) : null}
          </FormGrid>
        ) : null}

        {currentStep?.id === "source" && selectedType ? (
          <FormGrid>
            <FormField label={operationLabels.stepSource} required={currentStep.required}>
              <SelectInput
                value={form.sourceKind}
                onChange={(e) => {
                  const next = e.target.value as SourceKind | "";
                  update("sourceKind", next);
                  if (next !== "fair") update("sourceIds", []);
                }}
              >
                {selectedType.supported_sources.map((source) => (
                  <option key={source} value={source}>
                    {sourceKindLabels[source] ?? source}
                  </option>
                ))}
              </SelectInput>
              {form.sourceKind === "none" ? (
                <p className="text-muted">{operationLabels.sourceNoneHint}</p>
              ) : null}
            </FormField>
            {form.sourceKind === "fair" ? (
              <FairSourcePicker
                value={form.sourceIds}
                onChange={(ids) => update("sourceIds", ids)}
                error={fieldError}
              />
            ) : fieldError ? (
              <FieldError>{fieldError}</FieldError>
            ) : null}
          </FormGrid>
        ) : null}

        {currentStep?.id === "type_config" ? (
          <FormGrid>
            <FormField label="Başlık" required>
              <TextInput
                value={form.title}
                onChange={(e) => update("title", e.target.value)}
                maxLength={500}
              />
            </FormField>
            <FormField label="Açıklama">
              <TextareaInput
                value={form.description}
                onChange={(e) => update("description", e.target.value)}
                rows={3}
              />
            </FormField>
            {form.operationType === "manual_task" ? (
              <>
                <FormField label="Not">
                  <TextareaInput
                    value={form.note}
                    onChange={(e) => update("note", e.target.value)}
                    rows={3}
                  />
                </FormField>
                <FormField label="Müşteri ID (opsiyonel)">
                  <TextInput
                    value={form.customerId}
                    onChange={(e) => update("customerId", e.target.value)}
                  />
                </FormField>
                <FormField label="Son tarih">
                  <TextInput
                    type="datetime-local"
                    value={form.dueAt}
                    onChange={(e) => update("dueAt", e.target.value)}
                  />
                </FormField>
                <FormField label="Sorumlu kullanıcı ID">
                  <TextInput
                    value={form.assignedUserId}
                    onChange={(e) => update("assignedUserId", e.target.value)}
                  />
                </FormField>
                <FormField label="Öncelik">
                  <SelectInput
                    value={form.priority}
                    onChange={(e) => update("priority", e.target.value as OperationPriority)}
                  >
                    {Object.entries(operationPriorityLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </SelectInput>
                </FormField>
                <FormField label="Hatırlatma">
                  <TextInput
                    type="datetime-local"
                    value={form.reminderAt}
                    onChange={(e) => update("reminderAt", e.target.value)}
                  />
                </FormField>
              </>
            ) : (
              <Banner variant="info">
                Bu iş tipinin detay ayarları sonraki entegrasyon adımında genişletilecek. Şimdilik
                temel başlık/açıklama kaydedilir.
              </Banner>
            )}
            {fieldError ? <FieldError>{fieldError}</FieldError> : null}
          </FormGrid>
        ) : null}

        {currentStep?.id === "scope" ? (
          <div className="stack gap-sm">
            <p>{operationLabels.scopePreviewHint}</p>
            <p className="text-muted">
              Seçilen kaynak:{" "}
              {sourceKindLabels[form.sourceKind as SourceKind] ??
                (form.sourceKind || "—")}
            </p>
            {form.sourceKind === "fair" ? (
              <p className="text-muted">
                Fuar sayısı: {form.sourceIds.length}
              </p>
            ) : null}
          </div>
        ) : null}

        {currentStep?.id === "run_settings" ? (
          <FormGrid>
            {(selectedType?.capabilities.supports_retry ||
              ((selectedType?.run_settings_schema.fields as string[] | undefined) ?? []).includes(
                "retry",
              )) && (
              <CheckboxField
                id="operation-retry-enabled"
                checked={form.retryEnabled}
                onChange={(checked) => update("retryEnabled", checked)}
                label="Yeniden deneme"
              />
            )}
            <FormField label="Rate limit">
              <TextInput
                value={form.rateLimit}
                onChange={(e) => update("rateLimit", e.target.value)}
                placeholder="örn. 10"
              />
            </FormField>
            <FormField label="Eşzamanlılık">
              <TextInput
                value={form.concurrency}
                onChange={(e) => update("concurrency", e.target.value)}
                placeholder="örn. 2"
              />
            </FormField>
            {selectedType?.capabilities.supports_schedule ? (
              <FormField label="Zamanlama">
                <TextInput
                  value={form.schedule}
                  onChange={(e) => update("schedule", e.target.value)}
                  placeholder="cron veya ISO"
                />
              </FormField>
            ) : null}
            <FormField label="Öncelik">
              <SelectInput
                value={form.priority}
                onChange={(e) => update("priority", e.target.value as OperationPriority)}
              >
                {Object.entries(operationPriorityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          </FormGrid>
        ) : null}

        {currentStep?.id === "summary" || currentStep?.id === "confirm" ? (
          <div className="stack gap-md">
            <dl className="detail-grid">
              <div>
                <dt>İş tipi</dt>
                <dd>
                  {operationTypeLabels[form.operationType as OperationType] ?? form.operationType}
                </dd>
              </div>
              <div>
                <dt>Başlık</dt>
                <dd>{form.title || "—"}</dd>
              </div>
              <div>
                <dt>Kaynak</dt>
                <dd>
                  {sourceKindLabels[form.sourceKind as SourceKind] ??
                    (form.sourceKind || "—")}
                  {form.sourceKind === "fair" && form.sourceIds.length > 0
                    ? ` (${form.sourceIds.length})`
                    : ""}
                </dd>
              </div>
              <div>
                <dt>Öncelik</dt>
                <dd>{operationPriorityLabels[form.priority]}</dd>
              </div>
              {form.operationType === "manual_task" ? (
                <>
                  <div>
                    <dt>Müşteri</dt>
                    <dd>{form.customerId || "—"}</dd>
                  </div>
                  <div>
                    <dt>Son tarih</dt>
                    <dd>{form.dueAt || "—"}</dd>
                  </div>
                </>
              ) : null}
            </dl>
            {currentStep.id === "confirm" ? (
              <>
                {selectedType?.execution_ready ? (
                  <CheckboxField
                    id="operation-start-immediately"
                    checked={form.startImmediately}
                    onChange={(checked) => update("startImmediately", checked)}
                    label="Oluşturduktan sonra hemen başlat"
                  />
                ) : (
                  <Banner variant="info">{operationLabels.notExecutionReady}</Banner>
                )}
              </>
            ) : null}
          </div>
        ) : null}

        <div className="row gap-sm" style={{ marginTop: "1.25rem", flexWrap: "wrap" }}>
          <button type="button" className="btn secondary" onClick={onCancel} disabled={submitting}>
            Vazgeç
          </button>
          {stepIndex > 0 ? (
            <button type="button" className="btn secondary" onClick={goBack} disabled={submitting}>
              {operationLabels.back}
            </button>
          ) : null}
          {stepIndex < steps.length - 1 ? (
            <button type="button" className="btn primary" onClick={goNext} disabled={submitting}>
              {operationLabels.next}
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn secondary"
                disabled={submitting}
                onClick={() => void submit(false)}
              >
                {operationLabels.create}
              </button>
              {selectedType?.execution_ready ? (
                <button
                  type="button"
                  className="btn primary"
                  disabled={submitting}
                  onClick={() => void submit(true)}
                >
                  {operationLabels.createAndStart}
                </button>
              ) : null}
            </>
          )}
        </div>
      </Card>
    </PageShell>
  );
}
