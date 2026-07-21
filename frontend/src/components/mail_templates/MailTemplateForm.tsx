import React from "react";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { adminLabels } from "../../labels/adminLabels";
import { labels } from "../../labels";
import {
  CheckboxField,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextInput,
  TextareaInput,
} from "../ui/form";
import type { MailTemplate } from "../../types/mailTemplates";
import { Banner } from "../ui/Banner";
import {
  EMPTY_MAIL_TEMPLATE_FORM_VALUES,
  MAIL_TEMPLATE_TYPES,
  buildCreateMailTemplatePayload,
  buildUpdateMailTemplatePayload,
  mailTemplateToFormValues,
  validateMailTemplateFormValues,
  type MailTemplateFormValues,
} from "../../utils/mailTemplateForm";

interface MailTemplateFormProps {
  mode: "create" | "edit";
  initial?: MailTemplate | null;
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmitCreate: (payload: ReturnType<typeof buildCreateMailTemplatePayload>) => Promise<void>;
  onSubmitUpdate: (payload: ReturnType<typeof buildUpdateMailTemplatePayload>) => Promise<void>;
}

export function MailTemplateForm({
  mode,
  initial = null,
  saving,
  error,
  onCancel,
  onSubmitCreate,
  onSubmitUpdate,
}: MailTemplateFormProps) {
  const baseline = React.useMemo(
    () => (initial ? mailTemplateToFormValues(initial) : EMPTY_MAIL_TEMPLATE_FORM_VALUES),
    [initial],
  );
  const [values, setValues] = React.useState<MailTemplateFormValues>(baseline);
  const [localError, setLocalError] = React.useState<string | null>(null);
  const formError = localError ?? error;

  React.useEffect(() => {
    setValues(baseline);
    setLocalError(null);
  }, [baseline]);

  useReportFormDirty(values, baseline);
  const handleCancel = useModalFormCancel(onCancel);

  const setField = <K extends keyof MailTemplateFormValues>(
    key: K,
    value: MailTemplateFormValues[K],
  ) => {
    setValues((current) => ({ ...current, [key]: value }));
    setLocalError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validationError = validateMailTemplateFormValues(values);
    if (validationError) {
      setLocalError(validationError);
      return;
    }
    if (mode === "create") {
      await onSubmitCreate(buildCreateMailTemplatePayload(values));
      return;
    }
    await onSubmitUpdate(buildUpdateMailTemplatePayload(values, initial));
  };

  return (
    <form className="mail-template-form" onSubmit={(event) => void handleSubmit(event)}>
      {formError ? <Banner variant="error" className="form-form-alert">{formError}</Banner> : null}

      <FormSection title={adminLabels.mailTemplatesSectionGeneral}>
        <FormGrid>
          <FormField label={adminLabels.mailTemplatesFieldName} htmlFor="mail-template-name" required fullWidth>
            <TextInput
              id="mail-template-name"
              value={values.name}
              onChange={(event) => setField("name", event.target.value)}
              required
            />
          </FormField>

          <FormField
            label={adminLabels.mailTemplatesFieldKey}
            htmlFor="mail-template-key"
            required
            hint={adminLabels.mailTemplatesKeyHint}
          >
            <TextInput
              id="mail-template-key"
              value={values.key}
              onChange={(event) => setField("key", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.mailTemplatesFieldType} htmlFor="mail-template-type" required>
            <SelectInput
              id="mail-template-type"
              value={values.template_type}
              onChange={(event) =>
                setField("template_type", event.target.value as MailTemplateFormValues["template_type"])
              }
            >
              {MAIL_TEMPLATE_TYPES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField label={adminLabels.mailTemplatesFieldLanguage} htmlFor="mail-template-language" required>
            <TextInput
              id="mail-template-language"
              value={values.language}
              onChange={(event) => setField("language", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.mailTemplatesFieldSubject} htmlFor="mail-template-subject" required fullWidth>
            <TextInput
              id="mail-template-subject"
              value={values.subject}
              onChange={(event) => setField("subject", event.target.value)}
              required
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.mailTemplatesSectionContent}>
        <FormGrid>
          <FormField label={adminLabels.mailTemplatesFieldBodyHtml} htmlFor="mail-template-body-html" fullWidth>
            <TextareaInput
              id="mail-template-body-html"
              value={values.body_html}
              onChange={(event) => setField("body_html", event.target.value)}
              rows={8}
            />
          </FormField>

          <FormField label={adminLabels.mailTemplatesFieldBodyText} htmlFor="mail-template-body-text" fullWidth>
            <TextareaInput
              id="mail-template-body-text"
              value={values.body_text}
              onChange={(event) => setField("body_text", event.target.value)}
              rows={6}
            />
          </FormField>

          <FormField
            label={adminLabels.mailTemplatesFieldVariablesSchema}
            htmlFor="mail-template-variables-schema"
            fullWidth
          >
            <TextareaInput
              id="mail-template-variables-schema"
              value={values.variables_schema_json}
              onChange={(event) => setField("variables_schema_json", event.target.value)}
              rows={5}
              placeholder='{"customer_name": "string"}'
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.mailTemplatesSectionStatus}>
        <FormGrid>
          <CheckboxField
            id="mail-template-is-active"
            label={adminLabels.mailTemplatesFieldIsActive}
            checked={values.is_active}
            onChange={(checked) => setField("is_active", checked)}
          />
          <CheckboxField
            id="mail-template-is-default"
            label={adminLabels.mailTemplatesFieldIsDefault}
            checked={values.is_default}
            onChange={(checked) => setField("is_default", checked)}
            hint={values.is_default ? adminLabels.mailTemplatesDefaultHint : undefined}
          />
        </FormGrid>
      </FormSection>

      <FormActions
        onCancel={handleCancel}
        cancelLabel={labels.cancel}
        submitLabel={labels.save}
        saving={saving}
        savingLabel={adminLabels.mailTemplatesSaving}
      />
    </form>
  );
}
