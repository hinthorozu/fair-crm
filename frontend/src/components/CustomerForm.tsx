import React from "react";
import type { Customer, CreateCustomerPayload, CustomerStatus, CustomerType } from "../types/customer";
import {
  customerSourceLabels,
  customerStatusLabels,
  customerTypeLabels,
  labels,
} from "../labels";
import { emailPlaceholder, validateMultiEmailInput } from "../utils/email";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";

export type CustomerFormValues = CreateCustomerPayload;

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
  website: "",
  phone: "",
  email: "",
  source: "manual",
  description: "",
});

export function customerToFormValues(customer: Customer): CustomerFormValues {
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
    website: customer.website ?? "",
    phone: customer.phone ?? "",
    email: customer.email ?? "",
    source: customer.source,
    description: customer.description ?? "",
  };
}

export { emptyForm };

const typeOptions = Object.keys(customerTypeLabels) as CustomerType[];
const statusOptions: CustomerStatus[] = ["lead", "active", "inactive"];
const sourceOptions = Object.keys(customerSourceLabels) as Array<"manual" | "excel" | "scraper">;

interface CustomerFormProps {
  initial?: CustomerFormValues;
  submitLabel: string;
  onSubmit: (values: CustomerFormValues) => Promise<void>;
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

  const set = (field: keyof CustomerFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.display_name.trim()) {
      setError("Müşteri adı zorunludur.");
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
        display_name: values.display_name.trim(),
        legal_name: values.legal_name?.trim() || null,
        trade_name: values.trade_name?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        district: values.district?.trim() || null,
        address: values.address?.trim() || null,
        website: values.website?.trim() || null,
        phone: values.phone?.trim() || null,
        email: values.email?.trim() || null,
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
            onChange={(e) => set("customer_type", e.target.value)}
          >
            {typeOptions.map((t) => (
              <option key={t} value={t}>
                {customerTypeLabels[t]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={labels.status}>
          <select value={values.status} onChange={(e) => set("status", e.target.value)}>
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {customerStatusLabels[s]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={labels.source}>
          <select value={values.source} onChange={(e) => set("source", e.target.value)}>
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
        <Field label={labels.website}>
          <input value={values.website ?? ""} onChange={(e) => set("website", e.target.value)} />
        </Field>
        <Field label={labels.phone}>
          <input value={values.phone ?? ""} onChange={(e) => set("phone", e.target.value)} />
        </Field>
        <Field label={labels.email}>
          <input
            type="text"
            value={values.email ?? ""}
            onChange={(e) => set("email", e.target.value)}
            placeholder={emailPlaceholder}
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
