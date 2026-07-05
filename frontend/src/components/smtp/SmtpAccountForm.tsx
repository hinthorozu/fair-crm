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
} from "../ui/form";
import type { SmtpAccount } from "../../types/smtp";
import {
  EMPTY_SMTP_FORM_VALUES,
  SMTP_ENCRYPTION_TYPES,
  buildCreateSmtpPayload,
  buildUpdateSmtpPayload,
  getSmtpPortEncryptionHints,
  smtpAccountToFormValues,
  smtpPasswordSet,
  validateSmtpFormValues,
  type SmtpAccountFormValues,
} from "../../utils/smtpForm";

interface SmtpAccountFormProps {
  mode: "create" | "edit";
  initial?: SmtpAccount | null;
  saving: boolean;
  testing?: boolean;
  error: string | null;
  testError: string | null;
  testSuccess: string | null;
  onCancel: () => void;
  onSubmitCreate: (payload: ReturnType<typeof buildCreateSmtpPayload>) => Promise<void>;
  onSubmitUpdate: (payload: ReturnType<typeof buildUpdateSmtpPayload>) => Promise<void>;
  onTestMail?: (recipient: string) => Promise<void>;
}

export function SmtpAccountForm({
  mode,
  initial = null,
  saving,
  testing = false,
  error,
  testError,
  testSuccess,
  onCancel,
  onSubmitCreate,
  onSubmitUpdate,
  onTestMail,
}: SmtpAccountFormProps) {
  const baseline = React.useMemo(
    () => (initial ? smtpAccountToFormValues(initial) : EMPTY_SMTP_FORM_VALUES),
    [initial],
  );
  const [values, setValues] = React.useState<SmtpAccountFormValues>(baseline);
  const [testRecipient, setTestRecipient] = React.useState("");
  const [localError, setLocalError] = React.useState<string | null>(null);
  const formError = localError ?? error;

  React.useEffect(() => {
    setValues(baseline);
    setLocalError(null);
  }, [baseline]);

  useReportFormDirty(values, baseline);
  const handleCancel = useModalFormCancel(onCancel);

  const setField = <K extends keyof SmtpAccountFormValues>(
    key: K,
    value: SmtpAccountFormValues[K],
  ) => {
    setValues((current) => ({ ...current, [key]: value }));
    setLocalError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validationError = validateSmtpFormValues(values);
    if (validationError) {
      setLocalError(validationError);
      return;
    }
    if (mode === "create") {
      await onSubmitCreate(buildCreateSmtpPayload(values));
      return;
    }
    await onSubmitUpdate(buildUpdateSmtpPayload(values));
  };

  const passwordHint =
    mode === "edit" && initial && smtpPasswordSet(initial)
      ? adminLabels.smtpPasswordConfiguredHint
      : undefined;

  const portEncryptionHints = React.useMemo(
    () => getSmtpPortEncryptionHints(values.port, values.encryption_type),
    [values.port, values.encryption_type],
  );

  const serverWarnings = React.useMemo(() => {
    const warnings = new Set(portEncryptionHints);
    for (const warning of initial?.config_warnings ?? []) {
      warnings.add(warning);
    }
    return Array.from(warnings);
  }, [initial?.config_warnings, portEncryptionHints]);

  return (
    <form className="smtp-account-form" onSubmit={(event) => void handleSubmit(event)}>
      {formError ? <div className="banner error form-form-alert">{formError}</div> : null}

      <FormSection title={adminLabels.smtpSectionGeneral}>
        <FormGrid>
          <FormField label={adminLabels.smtpFieldName} htmlFor="smtp-name" required fullWidth>
            <TextInput
              id="smtp-name"
              type="text"
              value={values.name}
              onChange={(event) => setField("name", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.smtpFieldFromEmail} htmlFor="smtp-from-email" required>
            <TextInput
              id="smtp-from-email"
              type="email"
              value={values.from_email}
              onChange={(event) => setField("from_email", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.smtpFieldFromName} htmlFor="smtp-from-name">
            <TextInput
              id="smtp-from-name"
              type="text"
              value={values.from_name}
              onChange={(event) => setField("from_name", event.target.value)}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.smtpSectionServer}>
        <FormGrid>
          <FormField label={adminLabels.smtpFieldHost} htmlFor="smtp-host" required>
            <TextInput
              id="smtp-host"
              type="text"
              value={values.host}
              onChange={(event) => setField("host", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.smtpFieldPort} htmlFor="smtp-port" required>
            <TextInput
              id="smtp-port"
              type="number"
              min={1}
              max={65535}
              value={values.port}
              onChange={(event) => setField("port", event.target.value)}
              required
            />
          </FormField>

          <FormField label={adminLabels.smtpFieldEncryption} htmlFor="smtp-encryption" required>
            <SelectInput
              id="smtp-encryption"
              value={values.encryption_type}
              onChange={(event) =>
                setField(
                  "encryption_type",
                  event.target.value as SmtpAccountFormValues["encryption_type"],
                )
              }
            >
              {SMTP_ENCRYPTION_TYPES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FormGrid>
        {serverWarnings.length > 0 ? (
          <div className="banner info smtp-config-warning">
            <strong>{adminLabels.smtpConfigWarningTitle}</strong>
            <ul className="smtp-config-warning-list">
              {serverWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </FormSection>

      <FormSection title={adminLabels.smtpSectionAuth}>
        <FormGrid>
          <FormField label={adminLabels.smtpFieldUsername} htmlFor="smtp-username">
            <TextInput
              id="smtp-username"
              type="text"
              value={values.username}
              onChange={(event) => setField("username", event.target.value)}
              autoComplete="off"
            />
          </FormField>

          <FormField
            label={adminLabels.smtpFieldPassword}
            htmlFor="smtp-password"
            hint={passwordHint}
          >
            <TextInput
              id="smtp-password"
              type="password"
              value={values.password}
              onChange={(event) => setField("password", event.target.value)}
              autoComplete="new-password"
              placeholder={mode === "edit" ? adminLabels.smtpPasswordKeepPlaceholder : undefined}
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.smtpSectionStatus}>
        <FormGrid>
          <CheckboxField
            id="smtp-is-default"
            label={adminLabels.smtpFieldIsDefault}
            checked={values.is_default}
            onChange={(checked) => setField("is_default", checked)}
          />
          <CheckboxField
            id="smtp-is-active"
            label={adminLabels.smtpFieldIsActive}
            checked={values.is_active}
            onChange={(checked) => setField("is_active", checked)}
          />
        </FormGrid>
      </FormSection>

      {mode === "edit" && onTestMail ? (
        <FormSection title={adminLabels.smtpSectionTestMail}>
          <div className="smtp-test-mail-panel">
            <FormGrid>
              <FormField
                label={adminLabels.smtpFieldTestRecipient}
                htmlFor="smtp-test-recipient"
                fullWidth
              >
                <TextInput
                  id="smtp-test-recipient"
                  type="email"
                  value={testRecipient}
                  onChange={(event) => setTestRecipient(event.target.value)}
                  placeholder="admin@example.com"
                />
              </FormField>
            </FormGrid>
            {testError ? <div className="banner error">{testError}</div> : null}
            {testSuccess ? <div className="banner success">{testSuccess}</div> : null}
            <div className="smtp-test-mail-actions">
              <button
                type="button"
                className="btn secondary"
                disabled={testing || saving || !testRecipient.trim()}
                onClick={() => void onTestMail(testRecipient.trim())}
              >
                {testing ? adminLabels.smtpTestMailSending : adminLabels.smtpActionTestMail}
              </button>
            </div>
          </div>
        </FormSection>
      ) : null}

      <FormActions
        onCancel={handleCancel}
        cancelLabel={labels.cancel}
        submitLabel={labels.save}
        saving={saving}
        savingLabel={adminLabels.smtpSaving}
      />
    </form>
  );
}
