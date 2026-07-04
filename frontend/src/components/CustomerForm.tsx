import React from "react";
import type { CreateCustomerPayload, Customer, CustomerStatus, CustomerType } from "../types/customer";
import {
  customerSourceLabels,
  customerStatusLabels,
  customerTypeLabels,
  labels,
} from "../labels";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { CustomerCommunicationFieldList } from "./CustomerCommunicationFieldList";
import {
  type CommunicationFormItem,
  customerToCommunicationForm,
  formValuesToCustomerPayload,
  validateCommunicationEmails,
} from "../utils/customerCommunicationForm";

export interface CustomerFormValues {
  display_name: string;
  legal_name: string | null;
  trade_name: string | null;
  customer_type: CustomerType;
  status: CustomerStatus;
  country: string | null;
  city: string | null;
  district: string | null;
  address: string | null;
  description: string | null;
  instagram_url: string | null;
  facebook_url: string | null;
  linkedin_url: string | null;
  youtube_url: string | null;
  source: CreateCustomerPayload["source"];
  phones: CommunicationFormItem[];
  emails: CommunicationFormItem[];
  websites: CommunicationFormItem[];
}

const emptyForm = (): CustomerFormValues => ({
  display_name: "",
  legal_name: "",
  trade_name: "",
  customer_type: "lead",
  status: "active",
  country: "Türkiye",
  city: "",
  district: "",
  address: "",
  source: "manual",
  description: "",
  instagram_url: "",
  facebook_url: "",
  linkedin_url: "",
  youtube_url: "",
  phones: [],
  emails: [],
  websites: [],
});

export function customerToFormValues(customer: Customer): CustomerFormValues {
  const communications = customerToCommunicationForm(customer);
  return {
    display_name: customer.display_name,
    legal_name: customer.legal_name ?? "",
    trade_name: customer.trade_name ?? "",
    customer_type: customer.customer_type,
    status: customer.status === "archived" ? "active" : customer.status,
    country: customer.country ?? "",
    city: customer.city ?? "",
    district: customer.district ?? "",
    address: customer.address ?? "",
    source: customer.source,
    description: customer.description ?? "",
    instagram_url: customer.instagram_url ?? "",
    facebook_url: customer.facebook_url ?? "",
    linkedin_url: customer.linkedin_url ?? "",
    youtube_url: customer.youtube_url ?? "",
    phones: communications.phones,
    emails: communications.emails,
    websites: communications.websites,
  };
}

export { emptyForm };

const typeOptions = Object.keys(customerTypeLabels) as CustomerType[];
const statusOptions: CustomerStatus[] = ["lead", "active", "inactive"];
const sourceOptions = Object.keys(customerSourceLabels) as Array<"manual" | "excel" | "scraper">;

interface CustomerFormProps {
  initial?: CustomerFormValues;
  submitLabel: string;
  onSubmit: (values: CreateCustomerPayload) => Promise<void>;
  onCancel: () => void;
}

export function CustomerForm({ initial, submitLabel, onSubmit, onCancel }: CustomerFormProps) {
  const [values, setValues] = React.useState<CustomerFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = <K extends keyof CustomerFormValues>(field: K, value: CustomerFormValues[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.display_name.trim()) {
      setError("Müşteri adı zorunludur.");
      return;
    }
    const emailError = validateCommunicationEmails(values.emails);
    if (emailError) {
      setError(emailError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = formValuesToCustomerPayload({
        ...values,
        display_name: values.display_name.trim(),
        legal_name: values.legal_name?.trim() || null,
        trade_name: values.trade_name?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        district: values.district?.trim() || null,
        address: values.address?.trim() || null,
        description: values.description?.trim() || null,
        instagram_url: values.instagram_url?.trim() || null,
        facebook_url: values.facebook_url?.trim() || null,
        linkedin_url: values.linkedin_url?.trim() || null,
        youtube_url: values.youtube_url?.trim() || null,
      });
      await onSubmit(payload);
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
        <Field label={labels.display_name} required>
          <input
            value={values.display_name}
            onChange={(e) => set("display_name", e.target.value)}
            required
          />
        </Field>
        <Field label={labels.trade_name}>
          <input value={values.trade_name ?? ""} onChange={(e) => set("trade_name", e.target.value)} />
        </Field>
        <Field label={labels.legal_name}>
          <input value={values.legal_name ?? ""} onChange={(e) => set("legal_name", e.target.value)} />
        </Field>
        <Field label={labels.customer_type}>
          <select
            value={values.customer_type}
            onChange={(e) => set("customer_type", e.target.value as CustomerType)}
          >
            {typeOptions.map((t) => (
              <option key={t} value={t}>
                {customerTypeLabels[t]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={labels.status}>
          <select
            value={values.status}
            onChange={(e) => set("status", e.target.value as CustomerStatus)}
          >
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {customerStatusLabels[s]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={labels.source}>
          <select
            value={values.source}
            onChange={(e) => set("source", e.target.value as CustomerFormValues["source"])}
          >
            {sourceOptions.map((s) => (
              <option key={s} value={s}>
                {customerSourceLabels[s]}
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
        <Field label={labels.district}>
          <input value={values.district ?? ""} onChange={(e) => set("district", e.target.value)} />
        </Field>

        <CustomerCommunicationFieldList
          sectionLabel={labels.phone}
          items={values.phones}
          onChange={(phones) => set("phones", phones)}
          inputType="tel"
        />
        <CustomerCommunicationFieldList
          sectionLabel={labels.email}
          items={values.emails}
          onChange={(emails) => set("emails", emails)}
          inputType="email"
        />
        <CustomerCommunicationFieldList
          sectionLabel={labels.website}
          items={values.websites}
          onChange={(websites) => set("websites", websites)}
        />

        <Field label={labels.instagram}>
          <input
            type="url"
            value={values.instagram_url ?? ""}
            onChange={(e) => set("instagram_url", e.target.value)}
            placeholder="https://instagram.com/..."
          />
        </Field>
        <Field label={labels.facebook}>
          <input
            type="url"
            value={values.facebook_url ?? ""}
            onChange={(e) => set("facebook_url", e.target.value)}
            placeholder="https://facebook.com/..."
          />
        </Field>
        <Field label={labels.linkedin}>
          <input
            type="url"
            value={values.linkedin_url ?? ""}
            onChange={(e) => set("linkedin_url", e.target.value)}
            placeholder="https://linkedin.com/..."
          />
        </Field>
        <Field label={labels.youtube}>
          <input
            type="url"
            value={values.youtube_url ?? ""}
            onChange={(e) => set("youtube_url", e.target.value)}
            placeholder="https://youtube.com/..."
          />
        </Field>

        <Field label={labels.address} className="span-2">
          <textarea
            rows={2}
            value={values.address ?? ""}
            onChange={(e) => set("address", e.target.value)}
          />
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
