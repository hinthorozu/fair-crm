import React from "react";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { adminLabels } from "../../labels/adminLabels";
import { labels } from "../../labels";
import type { SmtpAccount } from "../../types/smtp";
import {
  EMPTY_SMTP_FORM_VALUES,
  SMTP_ENCRYPTION_TYPES,
  buildCreateSmtpPayload,
  buildUpdateSmtpPayload,
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

  return (
    <form className="smtp-account-form" onSubmit={(event) => void handleSubmit(event)}>
      <label className="form-field">
        <span>{adminLabels.smtpFieldName}</span>
        <input
          type="text"
          value={values.name}
          onChange={(event) => setField("name", event.target.value)}
          required
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldFromEmail}</span>
        <input
          type="email"
          value={values.from_email}
          onChange={(event) => setField("from_email", event.target.value)}
          required
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldFromName}</span>
        <input
          type="text"
          value={values.from_name}
          onChange={(event) => setField("from_name", event.target.value)}
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldHost}</span>
        <input
          type="text"
          value={values.host}
          onChange={(event) => setField("host", event.target.value)}
          required
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldPort}</span>
        <input
          type="number"
          min={1}
          max={65535}
          value={values.port}
          onChange={(event) => setField("port", event.target.value)}
          required
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldUsername}</span>
        <input
          type="text"
          value={values.username}
          onChange={(event) => setField("username", event.target.value)}
          autoComplete="off"
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldPassword}</span>
        {mode === "edit" && initial && smtpPasswordSet(initial) ? (
          <p className="text-muted smtp-password-hint">{adminLabels.smtpPasswordConfiguredHint}</p>
        ) : null}
        <input
          type="password"
          value={values.password}
          onChange={(event) => setField("password", event.target.value)}
          autoComplete="new-password"
          placeholder={mode === "edit" ? adminLabels.smtpPasswordKeepPlaceholder : undefined}
        />
      </label>

      <label className="form-field">
        <span>{adminLabels.smtpFieldEncryption}</span>
        <select
          value={values.encryption_type}
          onChange={(event) =>
            setField("encryption_type", event.target.value as SmtpAccountFormValues["encryption_type"])
          }
        >
          {SMTP_ENCRYPTION_TYPES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="form-field checkbox-field">
        <input
          type="checkbox"
          checked={values.is_default}
          onChange={(event) => setField("is_default", event.target.checked)}
        />
        <span>{adminLabels.smtpFieldIsDefault}</span>
      </label>

      <label className="form-field checkbox-field">
        <input
          type="checkbox"
          checked={values.is_active}
          onChange={(event) => setField("is_active", event.target.checked)}
        />
        <span>{adminLabels.smtpFieldIsActive}</span>
      </label>

      {(localError || error) && <p className="form-error">{localError ?? error}</p>}

      {mode === "edit" && onTestMail ? (
        <div className="smtp-test-mail-panel">
          <label className="form-field">
            <span>{adminLabels.smtpFieldTestRecipient}</span>
            <input
              type="email"
              value={testRecipient}
              onChange={(event) => setTestRecipient(event.target.value)}
              placeholder="admin@example.com"
            />
          </label>
          {testError ? <p className="form-error">{testError}</p> : null}
          {testSuccess ? <p className="form-success">{testSuccess}</p> : null}
          <button
            type="button"
            className="btn secondary"
            disabled={testing || saving || !testRecipient.trim()}
            onClick={() => void onTestMail(testRecipient.trim())}
          >
            {testing ? adminLabels.smtpTestMailSending : adminLabels.smtpActionTestMail}
          </button>
        </div>
      ) : null}

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={handleCancel} disabled={saving}>
          {labels.cancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? adminLabels.smtpSaving : labels.save}
        </button>
      </div>
    </form>
  );
}
