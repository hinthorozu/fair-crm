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
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { Banner } from "./ui/Banner";
import {
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextareaInput,
  TextInput,
} from "./ui/form";

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
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = <K extends keyof ActivityFormValues>(field: K, value: ActivityFormValues[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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
    <form className="activity-form" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}

      <FormSection title={activityLabels.activitySectionInfo}>
        <FormGrid>
          <FormField label={activityLabels.type} htmlFor="activity-type" required>
            <SelectInput
              id="activity-type"
              value={values.type}
              onChange={(event) => set("type", event.target.value as ActivityType)}
              required
            >
              {activityTypeOptions.map((option) => (
                <option key={option} value={option}>
                  {activityTypeLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField label={activityLabels.status} htmlFor="activity-status" required>
            <SelectInput
              id="activity-status"
              value={values.status}
              onChange={(event) => set("status", event.target.value as ActivityStatus)}
              required
            >
              {activityStatusOptions.map((option) => (
                <option key={option} value={option}>
                  {activityStatusLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField label={activityLabels.subject} htmlFor="activity-subject" required fullWidth>
            <TextInput
              id="activity-subject"
              type="text"
              value={values.subject}
              onChange={(event) => set("subject", event.target.value)}
              required
              maxLength={500}
            />
          </FormField>

          <FormField label={activityLabels.source} htmlFor="activity-source">
            <SelectInput
              id="activity-source"
              value={values.source ?? "manual"}
              onChange={(event) =>
                set("source", event.target.value as ActivityFormValues["source"])
              }
            >
              {activitySourceOptions.map((option) => (
                <option key={option} value={option}>
                  {activitySourceLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={activityLabels.activitySectionSchedule}>
        <FormGrid>
          <FormField label={activityLabels.activityDate} htmlFor="activity-date" required>
            <TextInput
              id="activity-date"
              type="datetime-local"
              value={values.activity_date}
              onChange={(event) => set("activity_date", event.target.value)}
              required
            />
          </FormField>

          <FormField label={activityLabels.followUpDate} htmlFor="activity-follow-up-date">
            <TextInput
              id="activity-follow-up-date"
              type="datetime-local"
              value={values.follow_up_date ?? ""}
              onChange={(event) => set("follow_up_date", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={activityLabels.activitySectionRelations}>
        <FormGrid>
          <FormField label={activityLabels.contact} htmlFor="activity-contact" fullWidth>
            <SelectInput
              id="activity-contact"
              value={values.contact_id ?? ""}
              onChange={(event) => set("contact_id", event.target.value || null)}
            >
              <option value="">{activityLabels.noContact}</option>
              {contacts.map((contact) => (
                <option key={contact.id} value={contact.id}>
                  {contact.full_name}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={activityLabels.activitySectionDetails}>
        <FormGrid>
          <FormField label={activityLabels.description} htmlFor="activity-description" fullWidth>
            <TextareaInput
              id="activity-description"
              rows={3}
              value={values.description ?? ""}
              onChange={(event) => set("description", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormActions
        onCancel={handleCancel}
        cancelLabel={activityLabels.cancel}
        submitLabel={submitLabel}
        saving={saving}
      />
    </form>
  );
}
