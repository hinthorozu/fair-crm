import React from "react";
import type { Contact, CreateContactPayload } from "../types/contact";
import { contactLabels } from "../labels/contactLabels";
import { emailPlaceholder, validateMultiEmailInput } from "../utils/email";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { Banner } from "./ui/Banner";
import {
  CheckboxField,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  TextareaInput,
  TextInput,
} from "./ui/form";

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
  email_allowed: true,
  sms_allowed: true,
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
    email_allowed: contact.email_allowed ?? true,
    sms_allowed: contact.sms_allowed ?? true,
  };
}

export { emptyForm };

interface ContactFormProps {
  initial?: ContactFormValues;
  submitLabel: string;
  onSubmit: (values: ContactFormValues) => Promise<void>;
  onCancel: () => void;
  customerEmailAllowed?: boolean;
  customerSmsAllowed?: boolean;
}

export function ContactForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
  customerEmailAllowed = true,
  customerSmsAllowed = true,
}: ContactFormProps) {
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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
        email_allowed: customerEmailAllowed ? values.email_allowed : false,
        sms_allowed: customerSmsAllowed ? values.sms_allowed : false,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : contactLabels.createError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="contact-form crm-form crm-form--standard" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}

      <FormSection title={contactLabels.contactSectionPerson}>
        <FormGrid>
          <FormField label={contactLabels.firstName} htmlFor="contact-first-name" required>
            <TextInput
              id="contact-first-name"
              value={values.first_name}
              onChange={(event) => set("first_name", event.target.value)}
              required
            />
          </FormField>

          <FormField label={contactLabels.lastName} htmlFor="contact-last-name" required>
            <TextInput
              id="contact-last-name"
              value={values.last_name}
              onChange={(event) => set("last_name", event.target.value)}
              required
            />
          </FormField>

          <FormField label={contactLabels.title} htmlFor="contact-title">
            <TextInput
              id="contact-title"
              value={values.title ?? ""}
              onChange={(event) => set("title", event.target.value)}
            />
          </FormField>

          <FormField label={contactLabels.department} htmlFor="contact-department">
            <TextInput
              id="contact-department"
              value={values.department ?? ""}
              onChange={(event) => set("department", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={contactLabels.contactSectionContact}>
        <FormGrid>
          <FormField
            label={contactLabels.email}
            htmlFor="contact-email"
            hint={emailPlaceholder}
            fullWidth
          >
            <TextInput
              id="contact-email"
              type="text"
              value={values.email ?? ""}
              onChange={(event) => set("email", event.target.value)}
              placeholder={emailPlaceholder}
            />
          </FormField>

          <FormField label={contactLabels.phone} htmlFor="contact-phone">
            <TextInput
              id="contact-phone"
              type="tel"
              value={values.phone ?? ""}
              onChange={(event) => set("phone", event.target.value)}
            />
          </FormField>

          <FormField label={contactLabels.mobilePhone} htmlFor="contact-mobile-phone">
            <TextInput
              id="contact-mobile-phone"
              type="tel"
              value={values.mobile_phone ?? ""}
              onChange={(event) => set("mobile_phone", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={contactLabels.contactSectionSocial}>
        <FormGrid>
          <FormField label={contactLabels.linkedin} htmlFor="contact-linkedin" fullWidth>
            <TextInput
              id="contact-linkedin"
              type="url"
              value={values.linkedin ?? ""}
              onChange={(event) => set("linkedin", event.target.value)}
              placeholder="https://linkedin.com/in/..."
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={contactLabels.contactSectionConsent}>
        <FormGrid>
          <CheckboxField
            id="contact-email-allowed"
            label={contactLabels.emailSendAllowed}
            checked={values.email_allowed ?? true}
            disabled={!customerEmailAllowed}
            onChange={(checked) => set("email_allowed", checked)}
          />
          <CheckboxField
            id="contact-sms-allowed"
            label={contactLabels.smsSendAllowed}
            checked={values.sms_allowed ?? true}
            disabled={!customerSmsAllowed}
            onChange={(checked) => set("sms_allowed", checked)}
          />
        </FormGrid>
        {!customerEmailAllowed ? (
          <p className="form-field-hint">{contactLabels.customerEmailConsentBlockedHint}</p>
        ) : null}
        {!customerSmsAllowed ? (
          <p className="form-field-hint">{contactLabels.customerSmsConsentBlockedHint}</p>
        ) : null}
      </FormSection>

      <FormSection title={contactLabels.contactSectionStatus}>
        <FormGrid>
          <CheckboxField
            id="contact-is-primary"
            label={contactLabels.isPrimary}
            checked={values.is_primary ?? false}
            onChange={(checked) => set("is_primary", checked)}
          />
          <CheckboxField
            id="contact-is-active"
            label={contactLabels.isActive}
            checked={values.is_active ?? true}
            onChange={(checked) => set("is_active", checked)}
          />
          <FormField label={contactLabels.notes} htmlFor="contact-notes" fullWidth>
            <TextareaInput
              id="contact-notes"
              rows={3}
              value={values.notes ?? ""}
              onChange={(event) => set("notes", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormActions
        onCancel={handleCancel}
        cancelLabel={contactLabels.cancel}
        submitLabel={submitLabel}
        saving={saving}
      />
    </form>
  );
}
