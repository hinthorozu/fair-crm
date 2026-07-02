import React from "react";
import type { Contact } from "../types/contact";
import type { Customer } from "../types/customer";
import type { Fair } from "../types/fair";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
  ParticipationStatus,
} from "../types/participation";
import {
  isoToLocalDatetime,
  localDatetimeToIso,
} from "./ActivityForm";
import {
  participationLabels,
  participationStatusLabels,
  participationStatusOptions,
} from "../labels/participationLabels";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";

export interface ParticipationFormValues {
  fair_id: string;
  customer_id: string;
  hall: string;
  stand: string;
  participation_status: ParticipationStatus;
  primary_contact_id: string;
  visited_at: string;
  notes: string;
}

const emptyForm = (): ParticipationFormValues => ({
  fair_id: "",
  customer_id: "",
  hall: "",
  stand: "",
  participation_status: "exhibitor",
  primary_contact_id: "",
  visited_at: "",
  notes: "",
});

export function participationToFormValues(p: {
  fair_id: string;
  customer_id: string;
  hall: string | null;
  stand: string | null;
  participation_status: ParticipationStatus;
  primary_contact_id: string | null;
  visited_at: string | null;
  notes: string | null;
}): ParticipationFormValues {
  return {
    fair_id: p.fair_id,
    customer_id: p.customer_id,
    hall: p.hall ?? "",
    stand: p.stand ?? "",
    participation_status: p.participation_status,
    primary_contact_id: p.primary_contact_id ?? "",
    visited_at: isoToLocalDatetime(p.visited_at),
    notes: p.notes ?? "",
  };
}

export function customerParticipationToFormValues(
  item: CustomerParticipationListItem,
  fairId: string,
): ParticipationFormValues {
  return {
    fair_id: fairId,
    customer_id: "",
    hall: item.hall ?? "",
    stand: item.stand ?? "",
    participation_status: item.participation_status,
    primary_contact_id: "",
    visited_at: isoToLocalDatetime(item.visited_at),
    notes: item.notes ?? "",
  };
}

export function fairParticipantToFormValues(
  item: FairParticipantListItem,
  customerId: string,
): ParticipationFormValues {
  return {
    fair_id: "",
    customer_id: customerId,
    hall: item.hall ?? "",
    stand: item.stand ?? "",
    participation_status: item.participation_status,
    primary_contact_id: "",
    visited_at: isoToLocalDatetime(item.visited_at),
    notes: item.notes ?? "",
  };
}

interface ParticipationFormProps {
  mode: "customer" | "fair";
  initial?: ParticipationFormValues;
  fairs?: Fair[];
  customers?: Customer[];
  contacts?: Contact[];
  submitLabel: string;
  onSubmit: (values: ParticipationFormValues) => Promise<void>;
  onCancel: () => void;
}

export function ParticipationForm({
  mode,
  initial,
  fairs = [],
  customers = [],
  contacts = [],
  submitLabel,
  onSubmit,
  onCancel,
}: ParticipationFormProps) {
  const [values, setValues] = React.useState<ParticipationFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = (field: keyof ParticipationFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "customer" && !values.fair_id) {
      setError(participationLabels.selectFair);
      return;
    }
    if (mode === "fair" && !values.customer_id) {
      setError(participationLabels.selectCompany);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kayıt kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="form-stack" onSubmit={(e) => void handleSubmit(e)}>
      {error && <div className="banner error">{error}</div>}

      {mode === "customer" && (
        <label className="form-field">
          <span>{participationLabels.fair} *</span>
          <select
            value={values.fair_id}
            onChange={(e) => set("fair_id", e.target.value)}
            required
          >
            <option value="">{participationLabels.selectFair}</option>
            {fairs.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {mode === "fair" && (
        <label className="form-field">
          <span>{participationLabels.company} *</span>
          <select
            value={values.customer_id}
            onChange={(e) => set("customer_id", e.target.value)}
            required
          >
            <option value="">{participationLabels.selectCompany}</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.display_name}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="form-row">
        <label className="form-field">
          <span>{participationLabels.hall}</span>
          <input value={values.hall} onChange={(e) => set("hall", e.target.value)} />
        </label>
        <label className="form-field">
          <span>{participationLabels.stand}</span>
          <input value={values.stand} onChange={(e) => set("stand", e.target.value)} />
        </label>
      </div>

      <label className="form-field">
        <span>{participationLabels.participationStatus}</span>
        <select
          value={values.participation_status}
          onChange={(e) => set("participation_status", e.target.value)}
        >
          {participationStatusOptions.map((s) => (
            <option key={s} value={s}>
              {participationStatusLabels[s]}
            </option>
          ))}
        </select>
      </label>

      {contacts.length > 0 && (
        <label className="form-field">
          <span>{participationLabels.primaryContact}</span>
          <select
            value={values.primary_contact_id}
            onChange={(e) => set("primary_contact_id", e.target.value)}
          >
            <option value="">{participationLabels.noContact}</option>
            {contacts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="form-field">
        <span>{participationLabels.visitedAt}</span>
        <input
          type="datetime-local"
          value={values.visited_at}
          onChange={(e) => set("visited_at", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>{participationLabels.notes}</span>
        <textarea
          rows={3}
          value={values.notes}
          onChange={(e) => set("notes", e.target.value)}
        />
      </label>

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={handleCancel} disabled={saving}>
          İptal
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? "Kaydediliyor…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

export function formValuesToCreatePayload(
  values: ParticipationFormValues,
  mode: "customer" | "fair",
  fixedId: string,
) {
  return {
    customer_id: mode === "customer" ? fixedId : values.customer_id,
    fair_id: mode === "fair" ? fixedId : values.fair_id,
    hall: values.hall.trim() || null,
    stand: values.stand.trim() || null,
    participation_status: values.participation_status,
    primary_contact_id: values.primary_contact_id || null,
    visited_at: values.visited_at ? localDatetimeToIso(values.visited_at) : null,
    notes: values.notes.trim() || null,
  };
}

export function formValuesToUpdatePayload(values: ParticipationFormValues) {
  return {
    hall: values.hall.trim() || null,
    stand: values.stand.trim() || null,
    participation_status: values.participation_status,
    primary_contact_id: values.primary_contact_id || null,
    visited_at: values.visited_at ? localDatetimeToIso(values.visited_at) : null,
    notes: values.notes.trim() || null,
  };
}
