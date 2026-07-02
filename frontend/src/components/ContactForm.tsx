import React from "react";
import type { Contact, CreateContactPayload } from "../types/contact";
import { contactLabels } from "../labels/contactLabels";
import { emailPlaceholder, validateMultiEmailInput } from "../utils/email";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";

export type ContactFormValues = Omit<CreateContactPayload, "customer_id">;

const emptyForm = (): ContactFormValues => ({
  first_name: "",
  last_name: "",
  title: "",
  department: "",
  email: "",
  phone: "",
  mobile_phone: "",
  linkedin: "",
  notes: "",
  is_primary: false,
  is_active: true,
});

export function contactToFormValues(contact: Contact): ContactFormValues {
  return {
    first_name: contact.first_name,
    last_name: contact.last_name,
    title: contact.title ?? "",
    department: contact.department ?? "",
    email: contact.email ?? "",
    phone: contact.phone ?? "",
    mobile_phone: contact.mobile_phone ?? "",
    linkedin: contact.linkedin ?? "",
    notes: contact.notes ?? "",
    is_primary: contact.is_primary,
    is_active: contact.is_active,
  };
}

export { emptyForm };

interface ContactFormProps {
  initial?: ContactFormValues;
  submitLabel: string;
  onSubmit: (values: ContactFormValues) => Promise<void>;
  onCancel: () => void;
}

export function ContactForm({ initial, submitLabel, onSubmit, onCancel }: ContactFormProps) {
  const [values, setValues] = React.useState<ContactFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = (field: keyof ContactFormValues, value: string | boolean) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.first_name.trim()) {
      setError(contactLabels.firstNameRequired);
      return;
    }
    if (!values.last_name.trim()) {
      setError(contactLabels.lastNameRequired);
      return;
    }
    const emailError = validateMultiEmailInput(values.email ?? "");
    if (emailError) {
      setError(emailError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        ...values,
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        title: values.title?.trim() || undefined,
        department: values.department?.trim() || undefined,
        email: values.email?.trim() || undefined,
        phone: values.phone?.trim() || undefined,
        mobile_phone: values.mobile_phone?.trim() || undefined,
        linkedin: values.linkedin?.trim() || undefined,
        notes: values.notes?.trim() || undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : contactLabels.createError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="form-grid" onSubmit={(e) => void handleSubmit(e)}>
      {error && <div className="banner error">{error}</div>}

      <label>
        {contactLabels.firstName} *
        <input
          value={values.first_name}
          onChange={(e) => set("first_name", e.target.value)}
          required
        />
      </label>

      <label>
        {contactLabels.lastName} *
        <input
          value={values.last_name}
          onChange={(e) => set("last_name", e.target.value)}
          required
        />
      </label>

      <label>
        {contactLabels.title}
        <input value={values.title ?? ""} onChange={(e) => set("title", e.target.value)} />
      </label>

      <label>
        {contactLabels.department}
        <input value={values.department ?? ""} onChange={(e) => set("department", e.target.value)} />
      </label>

      <label>
        {contactLabels.email}
        <input
          type="text"
          value={values.email ?? ""}
          onChange={(e) => set("email", e.target.value)}
          placeholder={emailPlaceholder}
        />
      </label>

      <label>
        {contactLabels.phone}
        <input value={values.phone ?? ""} onChange={(e) => set("phone", e.target.value)} />
      </label>

      <label>
        {contactLabels.mobilePhone}
        <input
          value={values.mobile_phone ?? ""}
          onChange={(e) => set("mobile_phone", e.target.value)}
        />
      </label>

      <label className="full-width">
        {contactLabels.linkedin}
        <input value={values.linkedin ?? ""} onChange={(e) => set("linkedin", e.target.value)} />
      </label>

      <label className="full-width">
        {contactLabels.notes}
        <textarea
          rows={3}
          value={values.notes ?? ""}
          onChange={(e) => set("notes", e.target.value)}
        />
      </label>

      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={values.is_primary ?? false}
          onChange={(e) => set("is_primary", e.target.checked)}
        />
        {contactLabels.isPrimary}
      </label>

      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={values.is_active ?? true}
          onChange={(e) => set("is_active", e.target.checked)}
        />
        {contactLabels.isActive}
      </label>

      <div className="form-actions full-width">
        <button type="button" className="btn secondary" onClick={handleCancel} disabled={saving}>
          {contactLabels.cancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? "…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
