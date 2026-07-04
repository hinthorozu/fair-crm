import React from "react";
import type { CreateFairPayload, Fair, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { labels } from "../labels";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { AdapterSelect } from "./AdapterSelect";
import {
  isValidSourceUrl,
  parseScraperConfigJson,
  scraperConfigToJsonText,
} from "../utils/fairIntegration";

export type FairFormValues = CreateFairPayload & {
  scraper_config_json: string;
};

const emptyForm = (): FairFormValues => ({
  name: "",
  organizer: "",
  venue: "",
  city: "",
  country: "Türkiye",
  start_date: "",
  end_date: "",
  website: "",
  status: "planned",
  description: "",
  adapter_key: "",
  source_url: "",
  scraper_config_json: "",
});

export function fairToFormValues(fair: Fair): FairFormValues {
  return {
    name: fair.name,
    organizer: fair.organizer ?? "",
    venue: fair.venue ?? "",
    city: fair.city ?? "",
    country: fair.country ?? "",
    start_date: fair.start_date ?? "",
    end_date: fair.end_date ?? "",
    website: fair.website ?? "",
    status: fair.status === "archived" ? "planned" : fair.status,
    description: fair.description ?? "",
    adapter_key: fair.adapter_key ?? "",
    source_url: fair.source_url ?? "",
    scraper_config_json: scraperConfigToJsonText(fair.scraper_config),
  };
}

export { emptyForm };

const statusOptions: FairStatus[] = ["planned", "active", "completed", "cancelled"];

interface FairFormProps {
  initial?: FairFormValues;
  submitLabel: string;
  onSubmit: (values: CreateFairPayload) => Promise<void>;
  onCancel: () => void;
}

export function FairForm({ initial, submitLabel, onSubmit, onCancel }: FairFormProps) {
  const [values, setValues] = React.useState<FairFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = (field: keyof FairFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const adapterSelected = Boolean(values.adapter_key?.trim());
  const sourceUrlRequired = adapterSelected;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.name.trim()) {
      setError(fairLabels.nameRequired);
      return;
    }

    const adapterKey = values.adapter_key?.trim() || null;
    const sourceUrlRaw = values.source_url?.trim() ?? "";
    const sourceUrl = sourceUrlRaw || null;

    if (adapterKey && !sourceUrl) {
      setError(fairLabels.sourceUrlRequired);
      return;
    }
    if (sourceUrl && !isValidSourceUrl(sourceUrl)) {
      setError(fairLabels.sourceUrlInvalid);
      return;
    }

    let scraperConfig: Record<string, unknown> | null = null;
    try {
      scraperConfig = parseScraperConfigJson(
        values.scraper_config_json,
        fairLabels.scraperConfigInvalid,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : fairLabels.scraperConfigInvalid);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: values.name.trim(),
        organizer: values.organizer?.trim() || null,
        venue: values.venue?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        start_date: values.start_date?.trim() || null,
        end_date: values.end_date?.trim() || null,
        website: values.website?.trim() || null,
        description: values.description?.trim() || null,
        status: values.status,
        adapter_key: adapterKey,
        source_url: sourceUrl,
        scraper_config: scraperConfig,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="customer-form" onSubmit={handleSubmit}>
      {error && <div className="banner error">{error}</div>}

      <div className="form-grid">
        <Field label={fairLabels.name} required>
          <input
            value={values.name}
            onChange={(e) => set("name", e.target.value)}
            required
          />
        </Field>
        <Field label={fairLabels.organizer}>
          <input value={values.organizer ?? ""} onChange={(e) => set("organizer", e.target.value)} />
        </Field>
        <Field label={fairLabels.venue}>
          <input value={values.venue ?? ""} onChange={(e) => set("venue", e.target.value)} />
        </Field>
        <Field label={labels.status}>
          <select value={values.status} onChange={(e) => set("status", e.target.value)}>
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {fairStatusLabels[s]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={labels.country}>
          <input value={values.country ?? ""} onChange={(e) => set("country", e.target.value)} />
        </Field>
        <Field label={labels.city}>
          <input value={values.city ?? ""} onChange={(e) => set("city", e.target.value)} />
        </Field>
        <Field label={fairLabels.start_date}>
          <input
            type="date"
            value={values.start_date ?? ""}
            onChange={(e) => set("start_date", e.target.value)}
          />
        </Field>
        <Field label={fairLabels.end_date}>
          <input
            type="date"
            value={values.end_date ?? ""}
            onChange={(e) => set("end_date", e.target.value)}
          />
        </Field>
        <Field label={labels.website}>
          <input value={values.website ?? ""} onChange={(e) => set("website", e.target.value)} />
        </Field>
        <Field label={labels.description} className="span-2">
          <textarea
            rows={3}
            value={values.description ?? ""}
            onChange={(e) => set("description", e.target.value)}
          />
        </Field>
      </div>

      <h3 className="section-title form-section-heading">{fairLabels.dataIntegration}</h3>

      <div className="form-grid">
        <Field label={fairLabels.adapter} className="span-2">
          <AdapterSelect
            value={values.adapter_key ?? ""}
            onChange={(adapterKey) => set("adapter_key", adapterKey)}
          />
        </Field>
        <Field label={fairLabels.sourceUrl} required={sourceUrlRequired} className="span-2">
          <input
            type="text"
            value={values.source_url ?? ""}
            onChange={(e) => set("source_url", e.target.value)}
            placeholder="https://"
            required={sourceUrlRequired}
          />
        </Field>
        <Field label={fairLabels.scraperConfig} className="span-2">
          <textarea
            rows={4}
            value={values.scraper_config_json}
            onChange={(e) => set("scraper_config_json", e.target.value)}
            placeholder={fairLabels.scraperConfigPlaceholder}
            spellCheck={false}
          />
        </Field>
      </div>

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={handleCancel} disabled={saving}>
          {labels.cancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? labels.loading : submitLabel}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
  required,
  className,
}: {
  label: string;
  children: React.ReactNode;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={`field ${className ?? ""}`}>
      <span>
        {label}
        {required && " *"}
      </span>
      {children}
    </label>
  );
}
