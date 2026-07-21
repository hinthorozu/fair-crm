import React from "react";
import {
  previewFairBulkEmailContent,
  previewFairBulkEmailRecipients,
  sendFairBulkEmail,
} from "../../api/fairBulkEmail";
import { listMailTemplates } from "../../api/mailTemplates";
import { listSmtpAccounts } from "../../api/smtp";
import { ApiError } from "../../api/client";
import { fairLabels } from "../../labels/fairLabels";
import { labels } from "../../labels";
import { adminLabels } from "../../labels/adminLabels";
import {
  canPerformMailTemplateAction,
  getGrantedMailTemplatePermissions,
} from "../../permissions/mailTemplatePermissions";
import type { Fair } from "../../types/fair";
import type { MailTemplate } from "../../types/mailTemplates";
import type { SmtpAccount } from "../../types/smtp";
import {
  DEFAULT_RECIPIENT_OPTIONS,
  type BulkEmailContentPreview,
  type RecipientOptions,
  type RecipientPreviewSummary,
  type SendBulkEmailResponse,
} from "../../types/fairBulkEmail";
import {
  formatMailTemplateOptionLabel,
  resolveSubjectAfterPreview,
  selectActiveMailTemplates,
} from "../../utils/mailTemplateForm";
import { CheckboxField, FormField, FormGrid, FormSection, SelectInput, TextInput } from "../ui/form";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import type { RecipientPreviewItem } from "../../types/fairBulkEmail";
import { Banner } from "../ui/Banner";

function skipReasonLabel(reason: string | null): string {
  switch (reason) {
    case "inactive_record":
      return fairLabels.bulkEmailSkipReasonInactive;
    case "no_email":
      return fairLabels.bulkEmailSkipReasonNoEmail;
    case "invalid_email":
      return fairLabels.bulkEmailSkipReasonInvalidEmail;
    case "duplicate_email":
      return fairLabels.bulkEmailSkipReasonDuplicate;
    default:
      return reason ?? "—";
  }
}

interface FairBulkEmailWizardProps {
  fair: Fair;
  canPreview: boolean;
  canSend: boolean;
  onCancel: () => void;
  onSent?: (result: SendBulkEmailResponse) => void;
}

export function FairBulkEmailWizard({
  fair,
  canPreview,
  canSend,
  onCancel,
  onSent,
}: FairBulkEmailWizardProps) {
  const mailTemplatePermissions = React.useMemo(() => getGrantedMailTemplatePermissions(), []);
  const canReadMailTemplates = canPerformMailTemplateAction(mailTemplatePermissions, "read");
  const canRenderMailTemplate = canPerformMailTemplateAction(mailTemplatePermissions, "render");

  const [recipientOptions, setRecipientOptions] = React.useState<RecipientOptions>(DEFAULT_RECIPIENT_OPTIONS);
  const [optionsSnapshot, setOptionsSnapshot] = React.useState(JSON.stringify(DEFAULT_RECIPIENT_OPTIONS));
  const [templates, setTemplates] = React.useState<MailTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = React.useState(true);
  const [smtpAccounts, setSmtpAccounts] = React.useState<SmtpAccount[]>([]);
  const [templateId, setTemplateId] = React.useState("");
  const [smtpAccountId, setSmtpAccountId] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [subjectTouched, setSubjectTouched] = React.useState(false);

  const [recipientPreview, setRecipientPreview] = React.useState<RecipientPreviewSummary | null>(null);
  const [contentPreview, setContentPreview] = React.useState<BulkEmailContentPreview | null>(null);
  const [previewReady, setPreviewReady] = React.useState(false);
  const [previewing, setPreviewing] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [templateError, setTemplateError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  const recipientPreviewColumns = React.useMemo<UniversalDataTableColumn<RecipientPreviewItem>[]>(
    () => [
      {
        key: "recipient_name",
        title: fairLabels.bulkEmailColRecipient,
        sortable: false,
        allowWrap: true,
        render: (item) => item.recipient_name ?? "—",
      },
      {
        key: "company_name",
        title: fairLabels.bulkEmailColCompany,
        sortable: false,
        allowWrap: true,
        render: (item) => item.company_name,
      },
      {
        key: "email",
        title: fairLabels.bulkEmailColEmail,
        sortable: false,
        allowWrap: true,
        render: (item) => item.email || "—",
      },
      {
        key: "source",
        title: fairLabels.bulkEmailColSource,
        sortable: false,
        render: (item) =>
          item.source === "contact"
            ? fairLabels.bulkEmailSourceContact
            : fairLabels.bulkEmailSourceCustomer,
      },
      {
        key: "status",
        title: fairLabels.bulkEmailColStatus,
        sortable: false,
        render: (item) =>
          item.status === "will_send"
            ? fairLabels.bulkEmailStatusWillSend
            : fairLabels.bulkEmailStatusSkip,
      },
      {
        key: "skip_reason",
        title: fairLabels.bulkEmailColSkipReason,
        sortable: false,
        allowWrap: true,
        render: (item) => skipReasonLabel(item.skip_reason),
      },
    ],
    [],
  );

  const selectedTemplate = templates.find((item) => item.id === templateId) ?? null;
  const previewStale = previewReady && JSON.stringify(recipientOptions) !== optionsSnapshot;
  const subjectValid = subject.trim().length > 0;
  const canRunPreview =
    canPreview &&
    canRenderMailTemplate &&
    Boolean(templateId) &&
    subjectValid &&
    !previewing &&
    !sending;
  const canSubmit =
    canSend &&
    previewReady &&
    !previewStale &&
    subjectValid &&
    templateId &&
    (recipientPreview?.deduped_recipient_count ?? 0) > 0 &&
    !previewing &&
    !sending;

  React.useEffect(() => {
    let cancelled = false;

    if (!canReadMailTemplates) {
      setTemplates([]);
      setTemplateId("");
      setTemplatesLoading(false);
      setTemplateError(fairLabels.bulkEmailTemplateReadDenied);
      return () => {
        cancelled = true;
      };
    }

    setTemplatesLoading(true);
    setTemplateError(null);

    void (async () => {
      try {
        const [templateResponse, smtpResponse] = await Promise.all([
          listMailTemplates(),
          listSmtpAccounts(),
        ]);
        if (cancelled) return;

        const activeTemplates = selectActiveMailTemplates(templateResponse.items);
        if (import.meta.env.DEV) {
          console.debug("[FairBulkEmailWizard] mail templates loaded", {
            total: templateResponse.items.length,
            active: activeTemplates.length,
            canReadMailTemplates,
            canRenderMailTemplate,
          });
        }

        setTemplates(activeTemplates);
        setSmtpAccounts(smtpResponse.items.filter((item) => item.is_active));

        if (activeTemplates.length === 0) {
          setTemplateId("");
          setTemplateError(fairLabels.bulkEmailNoTemplates);
        } else {
          const defaultTemplate =
            activeTemplates.find((item) => item.is_default) ?? activeTemplates[0] ?? null;
          if (defaultTemplate) {
            setTemplateId(defaultTemplate.id);
            setSubject(defaultTemplate.subject);
            setSubjectTouched(false);
          }
        }

        const defaultSmtp =
          smtpResponse.items.find((item) => item.is_active && item.is_default) ??
          smtpResponse.items.find((item) => item.is_active) ??
          null;
        setSmtpAccountId(defaultSmtp?.id ?? "");
      } catch (err) {
        if (!cancelled) {
          setTemplates([]);
          setTemplateId("");
          setTemplateError(
            err instanceof ApiError ? err.message : fairLabels.bulkEmailLoadTemplatesError,
          );
        }
      } finally {
        if (!cancelled) {
          setTemplatesLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [canReadMailTemplates]);

  React.useEffect(() => {
    if (selectedTemplate && !subjectTouched) {
      setSubject(selectedTemplate.subject);
    }
  }, [selectedTemplate, subjectTouched]);

  const invalidatePreview = () => {
    setPreviewReady(false);
    setRecipientPreview(null);
    setContentPreview(null);
  };

  const updateOption = <K extends keyof RecipientOptions>(key: K, value: RecipientOptions[K]) => {
    setRecipientOptions((current) => {
      const next = { ...current, [key]: value };
      if (previewReady && JSON.stringify(next) !== optionsSnapshot) {
        setPreviewReady(false);
      }
      return next;
    });
  };

  const handleSubjectChange = (value: string) => {
    setSubject(value);
    setSubjectTouched(true);
  };

  const handlePreview = async () => {
    if (!canPreview) {
      setError(fairLabels.bulkEmailPermissionPreviewDenied);
      return;
    }
    if (!canRenderMailTemplate) {
      setError(fairLabels.bulkEmailRenderPermissionDenied);
      return;
    }
    if (!templateId) {
      setError(fairLabels.bulkEmailNoTemplates);
      return;
    }
    if (!subjectValid) {
      setError(fairLabels.bulkEmailSubjectRequired);
      return;
    }
    setError(null);
    setSuccess(null);
    setPreviewing(true);
    try {
      const recipients = await previewFairBulkEmailRecipients(fair.id, recipientOptions);
      setRecipientPreview(recipients);
      if (recipients.deduped_recipient_count === 0) {
        invalidatePreview();
        setError(fairLabels.bulkEmailNoRecipients);
        return;
      }
      const content = await previewFairBulkEmailContent(fair.id, {
        template_id: templateId,
        subject_override: subjectTouched ? subject.trim() : null,
        recipient_options: recipientOptions,
      });
      setContentPreview(content);
      setSubject((current) => resolveSubjectAfterPreview(current, content.subject, subjectTouched));
      setOptionsSnapshot(JSON.stringify(recipientOptions));
      setPreviewReady(true);
    } catch (err) {
      invalidatePreview();
      setError(err instanceof ApiError ? err.message : fairLabels.bulkEmailError);
    } finally {
      setPreviewing(false);
    }
  };

  const handleSend = async () => {
    if (!canSubmit) return;
    setError(null);
    setSuccess(null);
    setSending(true);
    try {
      const result = await sendFairBulkEmail(fair.id, {
        template_id: templateId,
        smtp_account_id: smtpAccountId || null,
        subject_override: subject.trim(),
        recipient_options: recipientOptions,
      });
      setSuccess(result.message || fairLabels.bulkEmailSuccess);
      onSent?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.bulkEmailError);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="crm-form crm-form--wide fair-bulk-email-wizard">
      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
      {templateError ? <Banner variant="warning">{templateError}</Banner> : null}
      {!canRenderMailTemplate && canReadMailTemplates && templates.length > 0 ? (
        <Banner variant="warning">{fairLabels.bulkEmailRenderPermissionDenied}</Banner>
      ) : null}
      {previewStale ? <Banner variant="warning">{fairLabels.bulkEmailPreviewStale}</Banner> : null}
      {!previewReady && !previewStale ? (
        <Banner variant="info">{fairLabels.bulkEmailPreviewRequired}</Banner>
      ) : null}

      <FormSection title={fairLabels.bulkEmailOptionsSection}>
        <div className="checkbox-list">
          <CheckboxField
            id="fair-bulk-email-include-customer-emails"
            label={fairLabels.bulkEmailIncludeCustomerEmails}
            checked={recipientOptions.include_customer_emails}
            onChange={(checked) => updateOption("include_customer_emails", checked)}
            className="checkbox-row"
          />
          <CheckboxField
            id="fair-bulk-email-include-contact-emails"
            label={fairLabels.bulkEmailIncludeContactEmails}
            checked={recipientOptions.include_contact_emails}
            onChange={(checked) => updateOption("include_contact_emails", checked)}
            className="checkbox-row"
          />
          <CheckboxField
            id="fair-bulk-email-skip-no-email"
            label={fairLabels.bulkEmailSkipNoEmail}
            checked={recipientOptions.skip_no_email}
            onChange={(checked) => updateOption("skip_no_email", checked)}
            className="checkbox-row"
          />
          <CheckboxField
            id="fair-bulk-email-exclude-inactive"
            label={fairLabels.bulkEmailExcludeInactive}
            checked={recipientOptions.exclude_inactive}
            onChange={(checked) => updateOption("exclude_inactive", checked)}
            className="checkbox-row"
          />
          <CheckboxField
            id="fair-bulk-email-dedupe-emails"
            label={fairLabels.bulkEmailDedupeEmails}
            checked={recipientOptions.dedupe_emails}
            onChange={(checked) => updateOption("dedupe_emails", checked)}
            className="checkbox-row"
          />
        </div>
      </FormSection>

      <FormSection title={fairLabels.bulkEmailTemplateSection}>
        <FormGrid>
          <FormField label={adminLabels.navMailTemplates} htmlFor="fair-bulk-email-template" required fullWidth>
            <SelectInput
              id="fair-bulk-email-template"
              value={templateId}
              disabled={templatesLoading || !canReadMailTemplates || templates.length === 0}
              onChange={(event) => {
                setTemplateId(event.target.value);
                setSubjectTouched(false);
                invalidatePreview();
              }}
            >
              <option value="">
                {templatesLoading ? labels.loading : fairLabels.bulkEmailTemplatePlaceholder}
              </option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {formatMailTemplateOptionLabel(template, adminLabels.mailTemplatesDefaultBadge)}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField label={adminLabels.mailTemplatesTestEmailSmtpAccount} htmlFor="fair-bulk-email-smtp" fullWidth>
            <SelectInput
              id="fair-bulk-email-smtp"
              value={smtpAccountId}
              onChange={(event) => setSmtpAccountId(event.target.value)}
            >
              <option value="">{fairLabels.bulkEmailSmtpPlaceholder}</option>
              {smtpAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                  {account.is_default ? ` (${adminLabels.mailTemplatesDefaultBadge})` : ""}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField label={fairLabels.bulkEmailSubjectLabel} htmlFor="fair-bulk-email-subject" required fullWidth>
            <TextInput
              id="fair-bulk-email-subject"
              value={subject}
              onChange={(event) => handleSubjectChange(event.target.value)}
              required
            />
            {!subjectValid && subjectTouched ? (
              <span className="field-hint">{fairLabels.bulkEmailSubjectRequired}</span>
            ) : null}
          </FormField>
        </FormGrid>
        {canPreview ? (
          <div className="form-actions inline">
            <button
              type="button"
              className="btn secondary"
              disabled={!canRunPreview}
              onClick={() => void handlePreview()}
            >
              {previewing ? fairLabels.bulkEmailPreviewRunning : fairLabels.bulkEmailPreviewAction}
            </button>
          </div>
        ) : null}
      </FormSection>

      {recipientPreview && previewReady && !previewStale ? (
        <FormSection title={fairLabels.bulkEmailRecipientsSection}>
          <div className="detail-grid compact">
            <div>
              <strong>{fairLabels.bulkEmailSummaryCustomers}</strong>
              <div>{recipientPreview.total_customers}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailSummaryContacts}</strong>
              <div>{recipientPreview.total_contacts}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailSummaryValidEmails}</strong>
              <div>{recipientPreview.valid_email_count}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailSummaryDeduped}</strong>
              <div>{recipientPreview.deduped_recipient_count}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailSummarySkipped}</strong>
              <div>{recipientPreview.skipped_count}</div>
            </div>
          </div>
          <UniversalDataTable
            items={recipientPreview.recipients}
            columns={recipientPreviewColumns}
            rowKey={(item) => item.recipient_key}
            className="fair-bulk-email-recipients-table"
          />
        </FormSection>
      ) : null}

      {contentPreview && previewReady && !previewStale ? (
        <FormSection title={fairLabels.bulkEmailContentSection}>
          <div className="mail-template-preview-block">
            <h4>{fairLabels.bulkEmailSendSubject}</h4>
            <pre className="mail-template-preview-text">{subject.trim()}</pre>
            <p className="text-muted">{fairLabels.bulkEmailSendSubjectHint}</p>
          </div>
          {contentPreview.body_text ? (
            <div className="mail-template-preview-block">
              <h4>{adminLabels.mailTemplatesRenderedBodyText}</h4>
              <pre className="mail-template-preview-text">{contentPreview.body_text}</pre>
            </div>
          ) : null}
          {contentPreview.body_html ? (
            <div className="mail-template-preview-block">
              <h4>{adminLabels.mailTemplatesRenderedBodyHtml}</h4>
              <iframe
                className="mail-template-html-preview"
                title={adminLabels.mailTemplatesRenderedBodyHtml}
                sandbox=""
                srcDoc={contentPreview.body_html}
              />
            </div>
          ) : null}
        </FormSection>
      ) : null}

      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={onCancel} disabled={sending}>
          {labels.cancel}
        </button>
        {canSend ? (
          <button
            type="button"
            className="btn primary"
            disabled={!canSubmit}
            onClick={() => void handleSend()}
          >
            {sending ? fairLabels.bulkEmailSending : fairLabels.bulkEmailSubmit}
          </button>
        ) : (
          <span className="text-muted">{fairLabels.bulkEmailPermissionSendDenied}</span>
        )}
      </div>
    </div>
  );
}
