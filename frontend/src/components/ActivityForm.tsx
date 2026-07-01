import React from "react";
import type { Activity, ActivityStatus, ActivityType, CreateActivityPayload } from "../types/activity";
import type { Contact } from "../types/contact";
import {
  activityLabels,
  activitySourceLabels,
  activitySourceOptions,
  activityStatusLabels,
  activityStatusOptions,
  activityTypeLabels,
  activityTypeOptions,
} from "../labels/activityLabels";

export type ActivityFormValues = Omit<CreateActivityPayload, "customer_id">;

function nowLocalDatetime(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function isoToLocalDatetime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function localDatetimeToIso(local: string): string {
  if (!local) return "";
  return new Date(local).toISOString();
}

const emptyForm = (): ActivityFormValues => ({
  type: "call",
  subject: "",
  description: "",
  activity_date: nowLocalDatetime(),
  follow_up_date: "",
  status: "open",
  source: "manual",
  contact_id: null,
  is_active: true,
});

export function activityToFormValues(activity: Activity): ActivityFormValues {
  return {
    type: activity.type,
    subject: activity.subject,
    description: activity.description ?? "",
    activity_date: isoToLocalDatetime(activity.activity_date),
    follow_up_date: isoToLocalDatetime(activity.follow_up_date),
    status: activity.status,
    source: activity.source,
    contact_id: activity.contact_id,
    is_active: activity.is_active,
  };
}

export { emptyForm };

interface ActivityFormProps {
  initial?: ActivityFormValues;
  contacts: Contact[];
  submitLabel: string;
  onSubmit: (values: ActivityFormValues) => Promise<void>;
  onCancel: () => void;
}

export function ActivityForm({
  initial,
  contacts,
  submitLabel,
  onSubmit,
  onCancel,
}: ActivityFormProps) {
  const [values, setValues] = React.useState<ActivityFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = <K extends keyof ActivityFormValues>(field: K, value: ActivityFormValues[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.subject.trim()) {
      setError(activityLabels.subjectRequired);
      return;
    }
    if (!values.activity_date) {
      setError(activityLabels.activityDateRequired);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        ...values,
        subject: values.subject.trim(),
        description: values.description?.trim() || null,
        activity_date: localDatetimeToIso(values.activity_date),
        follow_up_date: values.follow_up_date
          ? localDatetimeToIso(values.follow_up_date)
          : null,
        contact_id: values.contact_id || null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="form-grid" onSubmit={(e) => void handleSubmit(e)}>
      {error && <div className="banner error">{error}</div>}

      <label>
        {activityLabels.type}
        <select
          value={values.type}
          onChange={(e) => set("type", e.target.value as ActivityType)}
          required
        >
          {activityTypeOptions.map((t) => (
            <option key={t} value={t}>
              {activityTypeLabels[t]}
            </option>
          ))}
        </select>
      </label>

      <label>
        {activityLabels.subject}
        <input
          type="text"
          value={values.subject}
          onChange={(e) => set("subject", e.target.value)}
          required
          maxLength={500}
        />
      </label>

      <label>
        {activityLabels.description}
        <textarea
          value={values.description ?? ""}
          onChange={(e) => set("description", e.target.value)}
          rows={3}
        />
      </label>

      <label>
        {activityLabels.activityDate}
        <input
          type="datetime-local"
          value={values.activity_date}
          onChange={(e) => set("activity_date", e.target.value)}
          required
        />
      </label>

      <label>
        {activityLabels.followUpDate}
        <input
          type="datetime-local"
          value={values.follow_up_date ?? ""}
          onChange={(e) => set("follow_up_date", e.target.value)}
        />
      </label>

      <label>
        {activityLabels.status}
        <select
          value={values.status}
          onChange={(e) => set("status", e.target.value as ActivityStatus)}
          required
        >
          {activityStatusOptions.map((s) => (
            <option key={s} value={s}>
              {activityStatusLabels[s]}
            </option>
          ))}
        </select>
      </label>

      <label>
        {activityLabels.source}
        <select
          value={values.source ?? "manual"}
          onChange={(e) => set("source", e.target.value as ActivityFormValues["source"])}
        >
          {activitySourceOptions.map((s) => (
            <option key={s} value={s}>
              {activitySourceLabels[s]}
            </option>
          ))}
        </select>
      </label>

      <label>
        {activityLabels.contact}
        <select
          value={values.contact_id ?? ""}
          onChange={(e) => set("contact_id", e.target.value || null)}
        >
          <option value="">{activityLabels.noContact}</option>
          {contacts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.full_name}
            </option>
          ))}
        </select>
      </label>

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={onCancel} disabled={saving}>
          {activityLabels.cancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? "..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
