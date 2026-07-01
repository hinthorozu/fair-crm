import React from "react";
import type { Fair, CreateFairPayload, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { labels } from "../labels";

export type FairFormValues = CreateFairPayload;

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
  };
}

export { emptyForm };

const statusOptions: FairStatus[] = ["planned", "active", "completed", "cancelled"];

interface FairFormProps {
  initial?: FairFormValues;
  submitLabel: string;
  onSubmit: (values: FairFormValues) => Promise<void>;
  onCancel: () => void;
}

export function FairForm({ initial, submitLabel, onSubmit, onCancel }: FairFormProps) {
  const [values, setValues] = React.useState<FairFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = (field: keyof FairFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.name.trim()) {
      setError(fairLabels.nameRequired);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        ...values,
        name: values.name.trim(),
        organizer: values.organizer?.trim() || null,
        venue: values.venue?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        start_date: values.start_date?.trim() || null,
        end_date: values.end_date?.trim() || null,
        website: values.website?.trim() || null,
        description: values.description?.trim() || null,
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

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={onCancel} disabled={saving}>
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
