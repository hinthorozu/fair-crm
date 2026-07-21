import React from "react";
import { renderMailTemplate, sendTestMailTemplate, ApiError } from "../../api/mailTemplates";
import { adminLabels } from "../../labels/adminLabels";
import { labels } from "../../labels";
import { FormField, FormGrid, FormSection, SelectInput, TextInput, TextareaInput } from "../ui/form";
import type { SmtpAccount } from "../../types/smtp";
import type { MailTemplate, RenderMailTemplateResponse } from "../../types/mailTemplates";
import {
  DEFAULT_RENDER_VARIABLES_JSON,
  formatMailTemplateTestEmailError,
  parseRenderVariablesJson,
  resolveSubjectAfterPreview,
} from "../../utils/mailTemplateForm";
import { formatSmtpTestMailError } from "../../utils/smtpForm";
import { Banner } from "../ui/Banner";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface MailTemplateTestEmailPanelProps {
  template: MailTemplate;
  smtpAccounts: SmtpAccount[];
  canRender: boolean;
  canTestSend: boolean;
  onCancel: () => void;
}

export function MailTemplateTestEmailPanel({
  template,
  smtpAccounts,
  canRender,
  canTestSend,
  onCancel,
}: MailTemplateTestEmailPanelProps) {
  const activeAccounts = React.useMemo(
    () => smtpAccounts.filter((account) => account.is_active),
    [smtpAccounts],
  );
  const defaultAccount = activeAccounts.find((account) => account.is_default) ?? activeAccounts[0];

  const [toEmail, setToEmail] = React.useState("");
  const [subject, setSubject] = React.useState(template.subject);
  const [subjectTouched, setSubjectTouched] = React.useState(false);
  const [smtpAccountId, setSmtpAccountId] = React.useState("");
  const [variablesJson, setVariablesJson] = React.useState(DEFAULT_RENDER_VARIABLES_JSON);
  const [variablesSnapshot, setVariablesSnapshot] = React.useState(DEFAULT_RENDER_VARIABLES_JSON);

  const [previewResult, setPreviewResult] = React.useState<RenderMailTemplateResponse | null>(null);
  const [previewReady, setPreviewReady] = React.useState(false);
  const [previewing, setPreviewing] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  React.useEffect(() => {
    setSmtpAccountId(defaultAccount?.id ?? "");
  }, [defaultAccount?.id]);

  React.useEffect(() => {
    setSubject(template.subject);
    setSubjectTouched(false);
    setPreviewResult(null);
    setPreviewReady(false);
    setVariablesJson(DEFAULT_RENDER_VARIABLES_JSON);
    setVariablesSnapshot(DEFAULT_RENDER_VARIABLES_JSON);
  }, [template.id]);

  const handleSubjectChange = (value: string) => {
    setSubject(value);
    setSubjectTouched(true);
  };

  const previewStale = previewReady && variablesJson.trim() !== variablesSnapshot.trim();

  const emailValid = EMAIL_PATTERN.test(toEmail.trim());
  const subjectValid = subject.trim().length > 0;
  const canSend =
    canTestSend &&
    previewReady &&
    !previewStale &&
    emailValid &&
    subjectValid &&
    !previewing &&
    !sending;

  const invalidatePreview = () => {
    setPreviewReady(false);
    setPreviewResult(null);
  };

  const handleVariablesChange = (value: string) => {
    setVariablesJson(value);
    if (previewReady && value.trim() !== variablesSnapshot.trim()) {
      setPreviewReady(false);
    }
  };

  const handlePreview = async () => {
    if (!canRender) {
      setError(adminLabels.mailTemplatesTestEmailRenderPermissionDenied);
      return;
    }
    setError(null);
    setSuccess(null);
    setPreviewing(true);
    try {
      if (!toEmail.trim()) {
        setError(adminLabels.mailTemplatesTestEmailRecipientRequired);
        return;
      }
      if (!EMAIL_PATTERN.test(toEmail.trim())) {
        setError(adminLabels.mailTemplatesTestEmailInvalidEmail);
        return;
      }
      let variables: Record<string, unknown>;
      try {
        variables = parseRenderVariablesJson(variablesJson) ?? {};
      } catch (parseErr) {
        setError(parseErr instanceof Error ? parseErr.message : adminLabels.mailTemplatesRenderError);
        return;
      }
      const result = await renderMailTemplate(template.id, { variables });
      setPreviewResult(result);
      setSubject((current) => resolveSubjectAfterPreview(current, result.subject, subjectTouched));
      setVariablesSnapshot(variablesJson.trim());
      setPreviewReady(true);
    } catch (err) {
      invalidatePreview();
      setError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesRenderError);
    } finally {
      setPreviewing(false);
    }
  };

  const handleSend = async () => {
    if (!canSend) return;
    setError(null);
    setSuccess(null);
    setSending(true);
    try {
      let variables: Record<string, unknown>;
      try {
        variables = parseRenderVariablesJson(variablesJson) ?? {};
      } catch (parseErr) {
        setError(parseErr instanceof Error ? parseErr.message : adminLabels.mailTemplatesRenderError);
        return;
      }
      const result = await sendTestMailTemplate(template.id, {
        to_email: toEmail.trim(),
        smtp_account_id: smtpAccountId || null,
        variables,
        subject_override: subject.trim(),
      });
      if (!result.success) {
        setError(formatSmtpTestMailError(result.message || adminLabels.mailTemplatesTestEmailError));
        return;
      }
      setSuccess(result.message || adminLabels.mailTemplatesTestEmailSuccess);
    } catch (err) {
      setError(
        formatSmtpTestMailError(
          formatMailTemplateTestEmailError(
            err,
            adminLabels.mailTemplatesTestEmailError,
            adminLabels.mailTemplatesTestEmailEndpointNotFound,
          ),
        ),
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="crm-form mail-template-test-email-panel">
      <p className="text-muted">
        {template.name} ({template.key})
      </p>

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
      {previewStale ? <Banner variant="warning">{adminLabels.mailTemplatesTestEmailPreviewStale}</Banner> : null}
      {!previewReady && !previewStale && canRender ? (
        <Banner variant="info">{adminLabels.mailTemplatesTestEmailPreviewRequired}</Banner>
      ) : null}

      <FormSection title={adminLabels.mailTemplatesTestEmailSection}>
        <FormGrid>
          <FormField
            label={adminLabels.mailTemplatesTestEmailRecipient}
            htmlFor="mail-template-test-email-recipient"
            required
            fullWidth
          >
            <TextInput
              id="mail-template-test-email-recipient"
              type="email"
              value={toEmail}
              onChange={(event) => setToEmail(event.target.value)}
              placeholder="test@example.com"
              required
            />
          </FormField>

          <FormField
            label={adminLabels.mailTemplatesTestEmailSubject}
            htmlFor="mail-template-test-email-subject"
            required
            fullWidth
          >
            <TextInput
              id="mail-template-test-email-subject"
              value={subject}
              onChange={(event) => handleSubjectChange(event.target.value)}
              placeholder={adminLabels.mailTemplatesFieldSubject}
              required
            />
            {!subjectValid && subjectTouched ? (
              <span className="field-hint">{adminLabels.mailTemplatesTestEmailSubjectRequired}</span>
            ) : null}
          </FormField>

          <FormField
            label={adminLabels.mailTemplatesTestEmailSmtpAccount}
            htmlFor="mail-template-test-email-smtp"
            fullWidth
          >
            <SelectInput
              id="mail-template-test-email-smtp"
              value={smtpAccountId}
              onChange={(event) => setSmtpAccountId(event.target.value)}
            >
              <option value="">{adminLabels.mailTemplatesTestEmailDefaultSmtp}</option>
              {activeAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                  {account.is_default ? ` (${adminLabels.mailTemplatesDefaultBadge})` : ""}
                </option>
              ))}
            </SelectInput>
          </FormField>

          <FormField
            label={adminLabels.mailTemplatesFieldSampleVariables}
            htmlFor="mail-template-test-email-variables"
            fullWidth
          >
            <TextareaInput
              id="mail-template-test-email-variables"
              value={variablesJson}
              onChange={(event) => handleVariablesChange(event.target.value)}
              rows={8}
              placeholder={DEFAULT_RENDER_VARIABLES_JSON}
            />
          </FormField>
        </FormGrid>

        {canRender ? (
          <div className="mail-template-test-email-preview-actions">
            <button
              type="button"
              className="btn secondary"
              disabled={previewing || sending}
              onClick={() => void handlePreview()}
            >
              {previewing
                ? adminLabels.mailTemplatesTestEmailPreviewRunning
                : adminLabels.mailTemplatesTestEmailPreviewAction}
            </button>
          </div>
        ) : null}
      </FormSection>

      {previewResult && previewReady && !previewStale ? (
        <FormSection title={adminLabels.mailTemplatesTestEmailPreviewSection}>
          <div className="mail-template-test-email-preview-output">
            <div className="mail-template-preview-block">
              <h4>{adminLabels.mailTemplatesTestEmailPreviewRecipient}</h4>
              <pre className="mail-template-preview-text">{toEmail.trim()}</pre>
            </div>
            <div className="mail-template-preview-block">
              <h4>{adminLabels.mailTemplatesTestEmailSendSubject}</h4>
              <pre className="mail-template-preview-text">{subject.trim()}</pre>
              <p className="text-muted">{adminLabels.mailTemplatesTestEmailSendSubjectHint}</p>
            </div>
            {previewResult.body_text ? (
              <div className="mail-template-preview-block">
                <h4>{adminLabels.mailTemplatesRenderedBodyText}</h4>
                <pre className="mail-template-preview-text">{previewResult.body_text}</pre>
              </div>
            ) : null}
            {previewResult.body_html ? (
              <div className="mail-template-preview-block">
                <h4>{adminLabels.mailTemplatesRenderedBodyHtml}</h4>
                <iframe
                  className="mail-template-html-preview"
                  title={adminLabels.mailTemplatesRenderedBodyHtml}
                  sandbox=""
                  srcDoc={previewResult.body_html}
                />
              </div>
            ) : null}
          </div>
        </FormSection>
      ) : null}

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={onCancel} disabled={sending}>
          {labels.cancel}
        </button>
        <button
          type="button"
          className="btn primary"
          disabled={!canSend}
          onClick={() => void handleSend()}
        >
          {sending ? adminLabels.mailTemplatesTestEmailSending : adminLabels.mailTemplatesTestEmailSubmit}
        </button>
      </div>
    </div>
  );
}
