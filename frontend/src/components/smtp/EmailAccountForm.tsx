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
  PasswordInput,
  RadioField,
  SelectInput,
  TextInput,
} from "../ui/form";
import type { EmailAccount, EmailAccountType } from "../../types/smtp";
import { Banner } from "../ui/Banner";
import {
  EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
  SMTP_ENCRYPTION_TYPES,
  buildCreateEmailAccountPayload,
  buildUpdateEmailAccountPayload,
  getSmtpPortEncryptionHints,
  emailAccountToFormValues,
  emailAccountPasswordSet,
  validateEmailAccountFormValues,
  type EmailAccountFormValues,
} from "../../utils/emailAccountForm";
import { ProviderAccountConfigPanel } from "./ProviderAccountConfigPanel";

export function resolveEmailAccountType(account?: EmailAccount | null): EmailAccountType {
  return account?.account_type === "provider" ? "provider" : "smtp";
}

interface EmailAccountFormProps {
  mode: "create" | "edit";
  initial?: EmailAccount | null;
  saving: boolean;
  testing?: boolean;
  error: string | null;
  testError: string | null;
  testSuccess: string | null;
  onCancel: () => void;
  onSubmitCreate: (payload: ReturnType<typeof buildCreateEmailAccountPayload>) => Promise<void>;
  onSubmitUpdate: (payload: ReturnType<typeof buildUpdateEmailAccountPayload>) => Promise<void>;
  onTestMail?: (recipient: string) => Promise<void>;
}

export function EmailAccountForm({
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
}: EmailAccountFormProps) {
  const baseline = React.useMemo(
    () => (initial ? emailAccountToFormValues(initial) : EMPTY_EMAIL_ACCOUNT_FORM_VALUES),
    [initial],
  );
  const [values, setValues] = React.useState<EmailAccountFormValues>(baseline);
  const [accountType, setAccountType] = React.useState<EmailAccountType>(() =>
    resolveEmailAccountType(initial),
  );
  const [testRecipient, setTestRecipient] = React.useState("");
  const [localError, setLocalError] = React.useState<string | null>(null);
  const formError = localError ?? error;
  const accountTypeLocked = mode === "edit";
  const providerSelected = accountType === "provider";
  const submitDisabled = saving || providerSelected;

  React.useEffect(() => {
    setValues(baseline);
    setAccountType(resolveEmailAccountType(initial));
    setLocalError(null);
  }, [baseline, initial]);

  useReportFormDirty({ ...values, accountType }, { ...baseline, accountType: resolveEmailAccountType(initial) });
  const handleCancel = useModalFormCancel(onCancel);

  const setField = <K extends keyof EmailAccountFormValues>(
    key: K,
    value: EmailAccountFormValues[K],
  ) => {
    setValues((current) => ({ ...current, [key]: value }));
    setLocalError(null);
  };

  const handleAccountTypeChange = (value: string) => {
    if (accountTypeLocked) return;
    setAccountType(value === "provider" ? "provider" : "smtp");
    setLocalError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (providerSelected) {
      setLocalError(adminLabels.smtpProviderSaveDisabledHint);
      return;
    }
    const validationError = validateEmailAccountFormValues(values, mode);
    if (validationError) {
      setLocalError(validationError);
      return;
    }
    if (mode === "create") {
      await onSubmitCreate(buildCreateEmailAccountPayload(values));
      return;
    }
    await onSubmitUpdate(buildUpdateEmailAccountPayload(values));
  };

  const passwordHint =
    mode === "edit" && initial && emailAccountPasswordSet(initial)
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
    <form
      className="email-account-form smtp-account-form crm-form crm-form--standard"
      onSubmit={(event) => void handleSubmit(event)}
    >
      {formError ? <Banner variant="error" className="form-form-alert">{formError}</Banner> : null}

      <FormSection title={adminLabels.smtpSectionAccountType}>
        <FormGrid>
          <RadioField
            id="email-account-type-smtp"
            name="email-account-type"
            label={adminLabels.smtpAccountTypeSmtp}
            value="smtp"
            checked={accountType === "smtp"}
            onChange={handleAccountTypeChange}
            disabled={accountTypeLocked}
          />
          <RadioField
            id="email-account-type-provider"
            name="email-account-type"
            label={adminLabels.smtpAccountTypeProvider}
            value="provider"
            checked={accountType === "provider"}
            onChange={handleAccountTypeChange}
            disabled={accountTypeLocked}
          />
        </FormGrid>
      </FormSection>

      {providerSelected ? (
        <ProviderAccountConfigPanel providerKey={initial?.provider_key ?? null} />
      ) : (
        <>
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
                      event.target.value as EmailAccountFormValues["encryption_type"],
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
              <Banner variant="info" className="smtp-config-warning">
                <strong>{adminLabels.smtpConfigWarningTitle}</strong>
                <ul className="smtp-config-warning-list">
                  {serverWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </Banner>
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
                <PasswordInput
                  id="smtp-password"
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
              {mode === "create" ? (
                <FormField
                  label={adminLabels.smtpFieldMaxDeliveryAttempts}
                  htmlFor="smtp-max-delivery-attempts"
                  required
                >
                  <SelectInput
                    id="smtp-max-delivery-attempts"
                    value={values.max_delivery_attempts}
                    onChange={(event) => setField("max_delivery_attempts", event.target.value)}
                    required
                  >
                    {[1, 2, 3, 4, 5].map((attempts) => (
                      <option key={attempts} value={String(attempts)}>
                        {attempts}
                      </option>
                    ))}
                  </SelectInput>
                </FormField>
              ) : (
                <FormField
                  label={adminLabels.smtpFieldMaxDeliveryAttempts}
                  htmlFor="smtp-max-delivery-attempts"
                >
                  <TextInput
                    id="smtp-max-delivery-attempts"
                    type="text"
                    value={values.max_delivery_attempts}
                    readOnly
                    disabled
                  />
                </FormField>
              )}
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
                {testError ? <Banner variant="error">{testError}</Banner> : null}
                {testSuccess ? <Banner variant="success">{testSuccess}</Banner> : null}
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
        </>
      )}

      {providerSelected ? (
        <Banner variant="warning">{adminLabels.smtpProviderSaveDisabledHint}</Banner>
      ) : null}

      <FormActions
        onCancel={handleCancel}
        cancelLabel={labels.cancel}
        submitLabel={labels.save}
        saving={saving}
        savingLabel={adminLabels.smtpSaving}
        submitDisabled={submitDisabled}
      />
    </form>
  );
}
