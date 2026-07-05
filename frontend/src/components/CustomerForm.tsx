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
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextareaInput,
  TextInput,
} from "./ui/form";
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

export function CustomerForm({ initial, submitLabel, onCancel, onSubmit }: CustomerFormProps) {
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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
    <form className="customer-form" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <div className="banner error form-form-alert">{error}</div> : null}

      <FormSection title={labels.customerSectionGeneral}>
        <FormGrid>
          <FormField label={labels.display_name} htmlFor="customer-display-name" required fullWidth>
            <TextInput
              id="customer-display-name"
              value={values.display_name}
              onChange={(event) => set("display_name", event.target.value)}
              required
            />
          </FormField>

          <FormField label={labels.trade_name} htmlFor="customer-trade-name">
            <TextInput
              id="customer-trade-name"
              value={values.trade_name ?? ""}
              onChange={(event) => set("trade_name", event.target.value)}
            />
          </FormField>

          <FormField label={labels.legal_name} htmlFor="customer-legal-name">
            <TextInput
              id="customer-legal-name"
              value={values.legal_name ?? ""}
              onChange={(event) => set("legal_name", event.target.value)}
            />
          </FormField>

          <FormField label={labels.customer_type} htmlFor="customer-type">
            <SelectInput
              id="customer-type"
              value={values.customer_type}
              onChange={(event) => set("customer_type", event.target.value as CustomerType)}
            >
              {typeOptions.map((option) => (
                <option key={option} value={option}>
                  {customerTypeLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField label={labels.status} htmlFor="customer-status">
            <SelectInput
              id="customer-status"
              value={values.status}
              onChange={(event) => set("status", event.target.value as CustomerStatus)}
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {customerStatusLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField label={labels.source} htmlFor="customer-source">
            <SelectInput
              id="customer-source"
              value={values.source}
              onChange={(event) =>
                set("source", event.target.value as CustomerFormValues["source"])
              }
            >
              {sourceOptions.map((option) => (
                <option key={option} value={option}>
                  {customerSourceLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={labels.customerSectionLocation}>
        <FormGrid>
          <FormField label={labels.country} htmlFor="customer-country">
            <TextInput
              id="customer-country"
              value={values.country ?? ""}
              onChange={(event) => set("country", event.target.value)}
            />
          </FormField>

          <FormField label={labels.city} htmlFor="customer-city">
            <TextInput
              id="customer-city"
              value={values.city ?? ""}
              onChange={(event) => set("city", event.target.value)}
            />
          </FormField>

          <FormField label={labels.district} htmlFor="customer-district">
            <TextInput
              id="customer-district"
              value={values.district ?? ""}
              onChange={(event) => set("district", event.target.value)}
            />
          </FormField>

          <FormField label={labels.address} htmlFor="customer-address" fullWidth>
            <TextareaInput
              id="customer-address"
              rows={2}
              value={values.address ?? ""}
              onChange={(event) => set("address", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={labels.customerSectionContact}>
        <FormGrid>
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
        </FormGrid>
      </FormSection>

      <FormSection title={labels.customerSectionSocial}>
        <FormGrid>
          <FormField label={labels.instagram} htmlFor="customer-instagram">
            <TextInput
              id="customer-instagram"
              type="url"
              value={values.instagram_url ?? ""}
              onChange={(event) => set("instagram_url", event.target.value)}
              placeholder="https://instagram.com/..."
            />
          </FormField>

          <FormField label={labels.facebook} htmlFor="customer-facebook">
            <TextInput
              id="customer-facebook"
              type="url"
              value={values.facebook_url ?? ""}
              onChange={(event) => set("facebook_url", event.target.value)}
              placeholder="https://facebook.com/..."
            />
          </FormField>

          <FormField label={labels.linkedin} htmlFor="customer-linkedin">
            <TextInput
              id="customer-linkedin"
              type="url"
              value={values.linkedin_url ?? ""}
              onChange={(event) => set("linkedin_url", event.target.value)}
              placeholder="https://linkedin.com/..."
            />
          </FormField>

          <FormField label={labels.youtube} htmlFor="customer-youtube">
            <TextInput
              id="customer-youtube"
              type="url"
              value={values.youtube_url ?? ""}
              onChange={(event) => set("youtube_url", event.target.value)}
              placeholder="https://youtube.com/..."
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={labels.customerSectionNotes}>
        <FormGrid>
          <FormField label={labels.description} htmlFor="customer-description" fullWidth>
            <TextareaInput
              id="customer-description"
              rows={3}
              value={values.description ?? ""}
              onChange={(event) => set("description", event.target.value)}
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
