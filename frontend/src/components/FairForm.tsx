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
import { Banner } from "./ui/Banner";
import {
  isValidSourceUrl,
  parseScraperConfigJson,
  scraperConfigToJsonText,
} from "../utils/fairIntegration";
import {
  buildFairSubmitPayload,
  isValidFairWebsite,
  parseFairDateInput,
  resolveAutoEndDate,
} from "../utils/fairForm";

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
  // Parent should remount via `key` when switching create/edit records.
  const [values, setValues] = React.useState<FairFormValues>(() => initial ?? emptyForm());
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [dateErrors, setDateErrors] = React.useState<{ start_date?: string; end_date?: string }>(
    {},
  );
  const baseline = React.useMemo(() => initial ?? emptyForm(), []);
  const endDateManualRef = React.useRef(Boolean((initial?.end_date ?? "").trim()));
  const handleCancel = useModalFormCancel(onCancel);

  useReportFormDirty(values, baseline);

  const set = (field: keyof FairFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleStartDateChange = (raw: string) => {
    set("start_date", raw);
    setDateErrors((prev) => ({ ...prev, start_date: undefined }));
  };

  const handleStartDateBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    const raw = event.target.value.trim();
    if (!raw) {
      setDateErrors((prev) => ({ ...prev, start_date: undefined }));
      return;
    }
    const parsed = parseFairDateInput(raw);
    if (!parsed) {
      setDateErrors((prev) => ({ ...prev, start_date: fairLabels.dateInvalid }));
      return;
    }
    setDateErrors((prev) => ({ ...prev, start_date: undefined }));
    setValues((prev) => {
      const endDate = prev.end_date ?? "";
      const nextEnd = resolveAutoEndDate({
        startDate: parsed,
        endDate,
        endDateManual: endDateManualRef.current,
      });
      return {
        ...prev,
        start_date: parsed,
        ...(nextEnd ? { end_date: nextEnd } : {}),
      };
    });
  };

  const handleEndDateChange = (raw: string) => {
    endDateManualRef.current = Boolean(raw.trim());
    set("end_date", raw);
    setDateErrors((prev) => ({ ...prev, end_date: undefined }));
  };

  const handleEndDateBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    const raw = event.target.value.trim();
    if (!raw) {
      endDateManualRef.current = false;
      setDateErrors((prev) => ({ ...prev, end_date: undefined }));
      return;
    }
    const parsed = parseFairDateInput(raw);
    if (!parsed) {
      setDateErrors((prev) => ({ ...prev, end_date: fairLabels.dateInvalid }));
      return;
    }
    endDateManualRef.current = true;
    setDateErrors((prev) => ({ ...prev, end_date: undefined }));
    if (parsed !== raw) {
      set("end_date", parsed);
    }
  };

  const adapterSelected = Boolean(values.adapter_key?.trim());
  const sourceUrlRequired = adapterSelected;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!values.name.trim()) {
      setError(fairLabels.nameRequired);
      return;
    }

    const startRaw = values.start_date?.trim() ?? "";
    const endRaw = values.end_date?.trim() ?? "";
    const nextDateErrors: { start_date?: string; end_date?: string } = {};
    let startDate = startRaw;
    let endDate = endRaw;

    if (startRaw) {
      const parsedStart = parseFairDateInput(startRaw);
      if (!parsedStart) {
        nextDateErrors.start_date = fairLabels.dateInvalid;
      } else {
        startDate = parsedStart;
      }
    }
    if (endRaw) {
      const parsedEnd = parseFairDateInput(endRaw);
      if (!parsedEnd) {
        nextDateErrors.end_date = fairLabels.dateInvalid;
      } else {
        endDate = parsedEnd;
      }
    }
    if (nextDateErrors.start_date || nextDateErrors.end_date) {
      setDateErrors(nextDateErrors);
      setError(fairLabels.dateInvalid);
      return;
    }
    if (startDate && endDate && endDate < startDate) {
      setDateErrors({ end_date: fairLabels.dateRangeInvalid });
      setError(fairLabels.dateRangeInvalid);
      return;
    }

    const websiteRaw = values.website?.trim() ?? "";
    if (websiteRaw && !isValidFairWebsite(websiteRaw)) {
      setError(fairLabels.websiteInvalid);
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
    setDateErrors({});
    try {
      await onSubmit(
        buildFairSubmitPayload(
          {
            ...values,
            start_date: startDate,
            end_date: endDate,
          },
          scraperConfig,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="fair-form crm-form crm-form--standard" onSubmit={(event) => void handleSubmit(event)}>
      {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}

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
          <FormField
            label={fairLabels.start_date}
            htmlFor="fair-start-date"
            hint={fairLabels.dateFormatHint}
            error={dateErrors.start_date}
          >
            <TextInput
              id="fair-start-date"
              type="date"
              placeholder={fairLabels.datePlaceholder}
              value={values.start_date ?? ""}
              onChange={(event) => handleStartDateChange(event.target.value)}
              onBlur={handleStartDateBlur}
              aria-invalid={Boolean(dateErrors.start_date)}
            />
          </FormField>

          <FormField
            label={fairLabels.end_date}
            htmlFor="fair-end-date"
            hint={fairLabels.dateFormatHint}
            error={dateErrors.end_date}
          >
            <TextInput
              id="fair-end-date"
              type="date"
              placeholder={fairLabels.datePlaceholder}
              value={values.end_date ?? ""}
              onChange={(event) => handleEndDateChange(event.target.value)}
              onBlur={handleEndDateBlur}
              aria-invalid={Boolean(dateErrors.end_date)}
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

          <FormField
            label={labels.website}
            htmlFor="fair-website"
            hint={fairLabels.websiteHint}
          >
            <TextInput
              id="fair-website"
              type="text"
              inputMode="url"
              autoComplete="url"
              value={values.website ?? ""}
              onChange={(event) => set("website", event.target.value)}
              placeholder={fairLabels.websitePlaceholder}
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
