import React from "react";
import type { CreateFairPayload, Fair, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { labels } from "../labels";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { AdapterSelect } from "./AdapterSelect";
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
  isValidSourceUrl,
  parseScraperConfigJson,
  scraperConfigToJsonText,
} from "../utils/fairIntegration";

export type FairFormValues = CreateFairPayload & {
  scraper_config_json: string;
};

const emptyForm = (): FairFormValues => ({
  name: "",
  organizer: "",
  venue: "",
  city: "",
  country: "Türkiye",
  start_date: "",
  end_date: "",
  website: "",
  status: "planned",
  description: "",
  adapter_key: "",
  source_url: "",
  scraper_config_json: "",
});

export function fairToFormValues(fair: Fair): FairFormValues {
  return {
    name: fair.name,
    organizer: fair.organizer ?? "",
    venue: fair.venue ?? "",
    city: fair.city ?? "",
    country: fair.country ?? "",
    start_date: fair.start_date ?? "",
    end_date: fair.end_date ?? "",
    website: fair.website ?? "",
    status: fair.status === "archived" ? "planned" : fair.status,
    description: fair.description ?? "",
    adapter_key: fair.adapter_key ?? "",
    source_url: fair.source_url ?? "",
    scraper_config_json: scraperConfigToJsonText(fair.scraper_config),
  };
}

export { emptyForm };

const statusOptions: FairStatus[] = ["planned", "active", "completed", "cancelled"];

interface FairFormProps {
  initial?: FairFormValues;
  submitLabel: string;
  onSubmit: (values: CreateFairPayload) => Promise<void>;
  onCancel: () => void;
}

export function FairForm({ initial, submitLabel, onSubmit, onCancel }: FairFormProps) {
  const [values, setValues] = React.useState<FairFormValues>(initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const baseline = React.useMemo(() => initial ?? emptyForm(), [initial]);
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    setValues(initial ?? emptyForm());
    setError(null);
  }, [initial]);

  const set = (field: keyof FairFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const adapterSelected = Boolean(values.adapter_key?.trim());
  const sourceUrlRequired = adapterSelected;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!values.name.trim()) {
      setError(fairLabels.nameRequired);
      return;
    }

    const adapterKey = values.adapter_key?.trim() || null;
    const sourceUrlRaw = values.source_url?.trim() ?? "";
    const sourceUrl = sourceUrlRaw || null;

    if (adapterKey && !sourceUrl) {
      setError(fairLabels.sourceUrlRequired);
      return;
    }
    if (sourceUrl && !isValidSourceUrl(sourceUrl)) {
      setError(fairLabels.sourceUrlInvalid);
      return;
    }

    let scraperConfig: Record<string, unknown> | null = null;
    try {
      scraperConfig = parseScraperConfigJson(
        values.scraper_config_json,
        fairLabels.scraperConfigInvalid,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : fairLabels.scraperConfigInvalid);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: values.name.trim(),
        organizer: values.organizer?.trim() || null,
        venue: values.venue?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        start_date: values.start_date?.trim() || null,
        end_date: values.end_date?.trim() || null,
        website: values.website?.trim() || null,
        description: values.description?.trim() || null,
        status: values.status,
        adapter_key: adapterKey,
        source_url: sourceUrl,
        scraper_config: scraperConfig,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="fair-form" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <div className="banner error form-form-alert">{error}</div> : null}

      <FormSection title={fairLabels.fairSectionInfo}>
        <FormGrid>
          <FormField label={fairLabels.name} htmlFor="fair-name" required fullWidth>
            <TextInput
              id="fair-name"
              value={values.name}
              onChange={(event) => set("name", event.target.value)}
              required
            />
          </FormField>

          <FormField label={labels.status} htmlFor="fair-status">
            <SelectInput
              id="fair-status"
              value={values.status}
              onChange={(event) => set("status", event.target.value)}
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {fairStatusLabels[option]}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={fairLabels.fairSectionScheduleLocation}>
        <FormGrid>
          <FormField label={fairLabels.start_date} htmlFor="fair-start-date">
            <TextInput
              id="fair-start-date"
              type="date"
              value={values.start_date ?? ""}
              onChange={(event) => set("start_date", event.target.value)}
            />
          </FormField>

          <FormField label={fairLabels.end_date} htmlFor="fair-end-date">
            <TextInput
              id="fair-end-date"
              type="date"
              value={values.end_date ?? ""}
              onChange={(event) => set("end_date", event.target.value)}
            />
          </FormField>

          <FormField label={labels.country} htmlFor="fair-country">
            <TextInput
              id="fair-country"
              value={values.country ?? ""}
              onChange={(event) => set("country", event.target.value)}
            />
          </FormField>

          <FormField label={labels.city} htmlFor="fair-city">
            <TextInput
              id="fair-city"
              value={values.city ?? ""}
              onChange={(event) => set("city", event.target.value)}
            />
          </FormField>

          <FormField label={fairLabels.venue} htmlFor="fair-venue" fullWidth>
            <TextInput
              id="fair-venue"
              value={values.venue ?? ""}
              onChange={(event) => set("venue", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={fairLabels.fairSectionOrganization}>
        <FormGrid>
          <FormField label={fairLabels.organizer} htmlFor="fair-organizer">
            <TextInput
              id="fair-organizer"
              value={values.organizer ?? ""}
              onChange={(event) => set("organizer", event.target.value)}
            />
          </FormField>

          <FormField label={labels.website} htmlFor="fair-website">
            <TextInput
              id="fair-website"
              type="url"
              value={values.website ?? ""}
              onChange={(event) => set("website", event.target.value)}
              placeholder="https://"
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={fairLabels.fairSectionDetails}>
        <FormGrid>
          <FormField label={labels.description} htmlFor="fair-description" fullWidth>
            <TextareaInput
              id="fair-description"
              rows={3}
              value={values.description ?? ""}
              onChange={(event) => set("description", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={fairLabels.dataIntegration}>
        <FormGrid>
          <FormField label={fairLabels.adapter} htmlFor="fair-adapter" fullWidth>
            <AdapterSelect
              id="fair-adapter"
              value={values.adapter_key ?? ""}
              onChange={(adapterKey) => set("adapter_key", adapterKey)}
            />
          </FormField>

          <FormField
            label={fairLabels.sourceUrl}
            htmlFor="fair-source-url"
            required={sourceUrlRequired}
            fullWidth
          >
            <TextInput
              id="fair-source-url"
              type="text"
              value={values.source_url ?? ""}
              onChange={(event) => set("source_url", event.target.value)}
              placeholder="https://"
              required={sourceUrlRequired}
            />
          </FormField>

          <FormField
            label={fairLabels.scraperConfig}
            htmlFor="fair-scraper-config"
            hint={fairLabels.scraperConfigPlaceholder}
            fullWidth
          >
            <TextareaInput
              id="fair-scraper-config"
              rows={4}
              value={values.scraper_config_json}
              onChange={(event) => set("scraper_config_json", event.target.value)}
              placeholder={fairLabels.scraperConfigPlaceholder}
              spellCheck={false}
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
