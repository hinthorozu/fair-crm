import React from "react";
import type { Contact } from "../types/contact";
import type { Customer } from "../types/customer";
import type { Fair } from "../types/fair";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
  ParticipationStatus,
} from "../types/participation";
import { labels } from "../labels";
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
import {
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextareaInput,
  TextInput,
} from "./ui/form";

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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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
    <form className="participation-form" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <div className="banner error form-form-alert">{error}</div> : null}

      <FormSection title={participationLabels.participationSectionInfo}>
        <FormGrid>
          {mode === "customer" ? (
            <FormField label={participationLabels.fair} htmlFor="participation-fair" required fullWidth>
              <SelectInput
                id="participation-fair"
                value={values.fair_id}
                onChange={(event) => set("fair_id", event.target.value)}
                required
              >
                <option value="">{participationLabels.selectFair}</option>
                {fairs.map((fair) => (
                  <option key={fair.id} value={fair.id}>
                    {fair.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          ) : null}

          {mode === "fair" ? (
            <FormField
              label={participationLabels.company}
              htmlFor="participation-company"
              required
              fullWidth
            >
              <SelectInput
                id="participation-company"
                value={values.customer_id}
                onChange={(event) => set("customer_id", event.target.value)}
                required
              >
                <option value="">{participationLabels.selectCompany}</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.display_name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          ) : null}

          <FormField label={participationLabels.hall} htmlFor="participation-hall">
            <TextInput
              id="participation-hall"
              value={values.hall}
              onChange={(event) => set("hall", event.target.value)}
            />
          </FormField>

          <FormField label={participationLabels.stand} htmlFor="participation-stand">
            <TextInput
              id="participation-stand"
              value={values.stand}
              onChange={(event) => set("stand", event.target.value)}
            />
          </FormField>

          <FormField
            label={participationLabels.participationStatus}
            htmlFor="participation-status"
          >
            <SelectInput
              id="participation-status"
              value={values.participation_status}
              onChange={(event) =>
                set("participation_status", event.target.value as ParticipationStatus)
              }
            >
              {participationStatusOptions.map((option) => (
                <option key={option} value={option}>
                  {participationStatusLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={participationLabels.participationSectionSchedule}>
        <FormGrid>
          <FormField label={participationLabels.visitedAt} htmlFor="participation-visited-at">
            <TextInput
              id="participation-visited-at"
              type="datetime-local"
              value={values.visited_at}
              onChange={(event) => set("visited_at", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      {contacts.length > 0 ? (
        <FormSection title={participationLabels.participationSectionRelations}>
          <FormGrid>
            <FormField
              label={participationLabels.primaryContact}
              htmlFor="participation-primary-contact"
              fullWidth
            >
              <SelectInput
                id="participation-primary-contact"
                value={values.primary_contact_id}
                onChange={(event) => set("primary_contact_id", event.target.value)}
              >
                <option value="">{participationLabels.noContact}</option>
                {contacts.map((contact) => (
                  <option key={contact.id} value={contact.id}>
                    {contact.full_name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          </FormGrid>
        </FormSection>
      ) : null}

      <FormSection title={participationLabels.participationSectionDetails}>
        <FormGrid>
          <FormField label={participationLabels.notes} htmlFor="participation-notes" fullWidth>
            <TextareaInput
              id="participation-notes"
              rows={3}
              value={values.notes}
              onChange={(event) => set("notes", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormActions
        onCancel={handleCancel}
        cancelLabel={labels.cancel}
        submitLabel={submitLabel}
        saving={saving}
        savingLabel={labels.loading}
      />
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
