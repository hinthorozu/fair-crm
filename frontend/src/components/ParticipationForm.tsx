import React from "react";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
} from "../types/participation";
import { labels } from "../labels";
import { participationLabels } from "../labels/participationLabels";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { CustomerEntitySelect } from "./CustomerEntitySelect";
import { FairEntitySelect } from "./FairEntitySelect";
import { Banner } from "./ui/Banner";
import {
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  TextareaInput,
  TextInput,
} from "./ui/form";

export interface ParticipationFormValues {
  fair_id: string;
  customer_id: string;
  hall: string;
  stand: string;
  notes: string;
}

const emptyForm = (): ParticipationFormValues => ({
  fair_id: "",
  customer_id: "",
  hall: "",
  stand: "",
  notes: "",
});

export function participationToFormValues(p: {
  fair_id: string;
  customer_id: string;
  hall: string | null;
  stand: string | null;
  notes: string | null;
}): ParticipationFormValues {
  return {
    fair_id: p.fair_id,
    customer_id: p.customer_id,
    hall: p.hall ?? "",
    stand: p.stand ?? "",
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
    notes: item.notes ?? "",
  };
}

interface ParticipationFormProps {
  mode: "customer" | "fair";
  initial?: ParticipationFormValues;
  submitLabel: string;
  onSubmit: (values: ParticipationFormValues) => Promise<void>;
  onCancel: () => void;
  /** When editing from customer context, fair is already fixed. */
  lockFair?: boolean;
  /** When editing from fair context, customer is already fixed. */
  lockCustomer?: boolean;
}

export function ParticipationForm({
  mode,
  initial,
  submitLabel,
  onSubmit,
  onCancel,
  lockFair = false,
  lockCustomer = false,
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
    <form className="participation-form crm-form crm-form--standard" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}

      <FormSection title={participationLabels.participationSectionInfo}>
        <FormGrid>
          {mode === "customer" ? (
            <FormField label={participationLabels.fair} htmlFor="participation-fair" required fullWidth>
              <FairEntitySelect
                id="participation-fair"
                value={values.fair_id}
                onChange={(fairId) => set("fair_id", fairId)}
                disabled={lockFair}
                placeholder={participationLabels.selectFair}
              />
            </FormField>
          ) : null}

          {mode === "fair" ? (
            <FormField
              label={participationLabels.company}
              htmlFor="participation-company"
              required
              fullWidth
            >
              <CustomerEntitySelect
                id="participation-company"
                value={values.customer_id}
                onChange={(customerId) => set("customer_id", customerId)}
                disabled={lockCustomer}
                placeholder={participationLabels.selectCompany}
              />
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
        </FormGrid>
      </FormSection>

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
    notes: values.notes.trim() || null,
  };
}

export function formValuesToUpdatePayload(values: ParticipationFormValues) {
  return {
    hall: values.hall.trim() || null,
    stand: values.stand.trim() || null,
    notes: values.notes.trim() || null,
  };
}
