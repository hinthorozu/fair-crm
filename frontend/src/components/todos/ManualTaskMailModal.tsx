import React from "react";
import { listContactsByCustomer } from "../../api/contacts";
import { getCustomer } from "../../api/customers";
import { listMailTemplates, renderMailTemplate } from "../../api/mailTemplates";
import { listSmtpAccounts } from "../../api/smtp";
import { sendManualTaskMail } from "../../api/todoWorklist";
import { ApiError } from "../../api/client";
import { todoLabels } from "../../labels/todoLabels";
import { todoWorklistLabels } from "../../labels/todoWorklistLabels";
import { adminLabels } from "../../labels/adminLabels";
import type { Customer } from "../../types/customer";
import type { MailTemplate } from "../../types/mailTemplates";
import type { SmtpAccount } from "../../types/smtp";
import {
  formatMailTemplateOptionLabel,
  selectActiveMailTemplates,
} from "../../utils/mailTemplateForm";
import { isValidSingleEmail, parseManualRecipientInput, splitEmailInputParts } from "../../utils/email";
import {
  buildManualMailCustomerVariables,
  buildManualMailPreviewSnapshot,
  hasUnresolvedTemplateMarkers,
  isManualMailPreviewStale,
  isUnresolvedVariableRenderError,
  resolveManualMailPreviewContent,
  toPreviewHtmlDocument,
  type ManualMailPreviewPayload,
  type ManualMailPreviewSnapshot,
} from "../../utils/manualTaskMailPreview";
import { FormField, FormGrid, FormSection, SelectInput, TextareaInput, TextInput } from "../ui/form";
import { FormModal } from "../ui/form/FormModal";
import { IconButton } from "../ui/IconButton";
import { LoadingState } from "../ui/LoadingState";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { Banner } from "../ui/Banner";
import { NavIconClose } from "../layout/NavIcons";

export interface ManualTaskMailModalProps {
  open: boolean;
  todoId: string;
  customerId: string;
  customerName?: string | null;
  onClose: () => void;
  onQueued?: (message: string) => void;
}

interface RecipientOption {
  value: string;
  label: string;
}

type ModalStep = "compose" | "preview";

const EMPTY_FORM = {
  recipients: [] as string[],
  smtpAccountId: "",
  templateId: "",
  subject: "",
  body: "",
  manualEmail: "",
};

function splitEmails(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .replace(/,/g, ";")
    .split(";")
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
}

function formatRecipientsPayload(recipients: string[]): string {
  if (recipients.length === 0) return "";
  return `${recipients.join("; ")};`;
}

export function ManualTaskMailModal({
  open,
  todoId,
  customerId,
  customerName,
  onClose,
  onQueued,
}: ManualTaskMailModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [loading, setLoading] = React.useState(true);
  const [sending, setSending] = React.useState(false);
  const [previewing, setPreviewing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [step, setStep] = React.useState<ModalStep>("compose");
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [recipientOptions, setRecipientOptions] = React.useState<RecipientOption[]>([]);
  const [templates, setTemplates] = React.useState<MailTemplate[]>([]);
  const [smtpAccounts, setSmtpAccounts] = React.useState<SmtpAccount[]>([]);
  const [recipients, setRecipients] = React.useState<string[]>([]);
  const [pickerValue, setPickerValue] = React.useState("");
  const [manualEmail, setManualEmail] = React.useState("");
  const [manualEmailError, setManualEmailError] = React.useState<string | null>(null);
  const [smtpAccountId, setSmtpAccountId] = React.useState("");
  const [templateId, setTemplateId] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [body, setBody] = React.useState("");
  const [subjectTouched, setSubjectTouched] = React.useState(false);
  const [bodyTouched, setBodyTouched] = React.useState(false);
  const [previewPayload, setPreviewPayload] = React.useState<ManualMailPreviewPayload | null>(null);
  const [previewSnapshot, setPreviewSnapshot] = React.useState<ManualMailPreviewSnapshot | null>(null);

  const formValues = React.useMemo(
    () => ({ recipients, smtpAccountId, templateId, subject, body, manualEmail }),
    [recipients, smtpAccountId, templateId, subject, body, manualEmail],
  );
  useReportFormDirty(formValues, EMPTY_FORM);

  const currentSnapshot = React.useMemo(
    () =>
      buildManualMailPreviewSnapshot({
        recipients,
        smtpAccountId,
        templateId,
        subject,
        body,
      }),
    [recipients, smtpAccountId, templateId, subject, body],
  );
  const previewStale = isManualMailPreviewStale(previewSnapshot, currentSnapshot);

  React.useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSuccess(null);
    setStep("compose");
    setCustomer(null);
    setRecipients([]);
    setPickerValue("");
    setManualEmail("");
    setManualEmailError(null);
    setSmtpAccountId("");
    setTemplateId("");
    setSubject("");
    setBody("");
    setSubjectTouched(false);
    setBodyTouched(false);
    setPreviewPayload(null);
    setPreviewSnapshot(null);

    void (async () => {
      try {
        const [customerResponse, contactsResponse, templateResponse, smtpResponse] =
          await Promise.all([
            getCustomer(customerId),
            listContactsByCustomer(customerId, { pageSize: 100 }),
            listMailTemplates(),
            listSmtpAccounts(),
          ]);
        if (cancelled) return;

        setCustomer(customerResponse);

        const options: RecipientOption[] = [];
        const seen = new Set<string>();
        const addOption = (email: string, label: string) => {
          const normalized = email.trim().toLowerCase();
          if (!normalized || seen.has(normalized) || !isValidSingleEmail(normalized)) return;
          seen.add(normalized);
          options.push({ value: normalized, label });
        };

        for (const item of customerResponse.emails ?? []) {
          addOption(item.email, `${todoWorklistLabels.manualMailCustomerEmail}: ${item.email}`);
        }
        if (customerResponse.email) {
          for (const email of splitEmails(customerResponse.email)) {
            addOption(email, `${todoWorklistLabels.manualMailCustomerEmail}: ${email}`);
          }
        }
        for (const contact of contactsResponse.items) {
          const contactName =
            contact.full_name || `${contact.first_name} ${contact.last_name}`.trim();
          for (const email of splitEmails(contact.email)) {
            addOption(
              email,
              `${todoWorklistLabels.manualMailContactEmail}: ${contactName} <${email}>`,
            );
          }
        }
        setRecipientOptions(options);

        const activeTemplates = selectActiveMailTemplates(templateResponse.items);
        setTemplates(activeTemplates);

        const activeSmtp = smtpResponse.items.filter((item) => item.is_active);
        setSmtpAccounts(activeSmtp);
        const defaultSmtp =
          activeSmtp.find((item) => item.is_default) ?? activeSmtp[0] ?? null;
        setSmtpAccountId(defaultSmtp?.id ?? "");
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : todoWorklistLabels.manualMailLoadError,
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, customerId]);

  const invalidatePreview = () => {
    setPreviewPayload(null);
    setPreviewSnapshot(null);
    if (step === "preview") {
      setStep("compose");
    }
  };

  const addRecipient = (email: string): boolean => {
    const result = parseManualRecipientInput(email, recipients);
    if (result.error) {
      setManualEmailError(result.error);
      return false;
    }
    if (result.emails.length === 0) {
      if (splitEmailInputParts(email).length > 0) {
        setManualEmailError(todoWorklistLabels.manualMailDuplicateEmail);
      }
      return false;
    }
    setRecipients((current) => [...current, ...result.emails]);
    setManualEmailError(null);
    invalidatePreview();
    return true;
  };

  const handlePickerChange = (value: string) => {
    setPickerValue("");
    if (!value) return;
    addRecipient(value);
  };

  const handleAddManualEmail = () => {
    if (addRecipient(manualEmail)) {
      setManualEmail("");
    }
  };

  const handleManualEmailKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === "," || event.key === ";") {
      event.preventDefault();
      handleAddManualEmail();
    }
  };

  const handleTemplateChange = (value: string) => {
    setTemplateId(value);
    setSubjectTouched(false);
    setBodyTouched(false);
    invalidatePreview();
    if (!value) return;
    const selected = templates.find((item) => item.id === value);
    if (!selected) return;
    setSubject(selected.subject);
    setBody(selected.body_html || selected.body_text || "");
  };

  const formComplete =
    recipients.length > 0 &&
    Boolean(smtpAccountId) &&
    subject.trim().length > 0 &&
    body.trim().length > 0;

  const canPreview = formComplete && !previewing && !sending && !loading;
  const canSendFromPreview =
    step === "preview" &&
    Boolean(previewPayload) &&
    !previewPayload?.unresolvedVariables &&
    !previewStale &&
    !sending &&
    !previewing;

  const handlePreview = async () => {
    if (!canPreview) {
      setError(todoWorklistLabels.manualMailPreviewFormIncomplete);
      return;
    }

    setPreviewing(true);
    setError(null);
    setSuccess(null);

    try {
      const selectedTemplate = templates.find((item) => item.id === templateId) ?? null;
      const selectedSmtp = smtpAccounts.find((item) => item.id === smtpAccountId) ?? null;
      if (!selectedSmtp) {
        setError(todoWorklistLabels.manualMailPreviewFormIncomplete);
        return;
      }

      let unresolvedVariables = false;
      let renderedSubject: string | null = null;
      let renderedBodyHtml: string | null = null;
      let renderedBodyText: string | null = null;

      if (selectedTemplate && customer) {
        try {
          const rendered = await renderMailTemplate(selectedTemplate.id, {
            variables: buildManualMailCustomerVariables(customer),
          });
          renderedSubject = rendered.subject;
          renderedBodyHtml = rendered.body_html;
          renderedBodyText = rendered.body_text;
        } catch (err) {
          const message = err instanceof ApiError ? err.message : String(err);
          if (isUnresolvedVariableRenderError(message)) {
            unresolvedVariables = true;
          } else {
            setError(message || todoWorklistLabels.manualMailLoadError);
            return;
          }
        }
      }

      const resolved = resolveManualMailPreviewContent({
        template: selectedTemplate,
        formSubject: subject,
        formBody: body,
        subjectTouched,
        bodyTouched,
        renderedSubject,
        renderedBodyHtml,
        renderedBodyText,
      });

      if (
        hasUnresolvedTemplateMarkers(resolved.subject) ||
        hasUnresolvedTemplateMarkers(resolved.body)
      ) {
        unresolvedVariables = true;
      }

      if (!subjectTouched && renderedSubject) {
        setSubject(resolved.subject);
      }
      if (!bodyTouched && (renderedBodyHtml || renderedBodyText)) {
        setBody(resolved.body);
      }

      const snapshot = buildManualMailPreviewSnapshot({
        recipients,
        smtpAccountId,
        templateId,
        subject: resolved.subject,
        body: resolved.body,
      });

      setPreviewSnapshot(snapshot);
      setPreviewPayload({
        ...snapshot,
        templateName: selectedTemplate?.name ?? null,
        smtpAccountName: selectedSmtp.name,
        htmlDocument: toPreviewHtmlDocument(resolved.body),
        unresolvedVariables,
      });
      setStep("preview");
    } finally {
      setPreviewing(false);
    }
  };

  const handleSendFromPreview = async () => {
    if (!canSendFromPreview || !previewPayload || sending) return;

    setSending(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await sendManualTaskMail(todoId, customerId, {
        todo_id: todoId,
        customer_id: customerId,
        smtp_account_id: previewPayload.smtpAccountId,
        template_id: previewPayload.templateId || null,
        recipients: formatRecipientsPayload(previewPayload.recipients),
        subject: previewPayload.subject,
        body: previewPayload.body,
      });
      const message = result.message || todoWorklistLabels.manualMailQueuedSuccess;
      setSuccess(message);
      onQueued?.(message);
      setTimeout(() => {
        onClose();
      }, 600);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : todoWorklistLabels.manualMailSendError);
    } finally {
      setSending(false);
    }
  };

  if (!open) return null;

  const title = customerName
    ? `${todoWorklistLabels.manualMailModalTitle} — ${customerName}`
    : todoWorklistLabels.manualMailModalTitle;

  return (
    <FormModal title={title} onClose={requestClose} size="lg">
      {loading ? (
        <div className="todo-worklist-modal-loading">
          <LoadingState variant="inline" />
        </div>
      ) : step === "preview" && previewPayload ? (
        <div className="manual-task-mail-preview">
          {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}
          {success ? <Banner variant="success" className="form-form-alert">{success}</Banner> : null}
          {previewPayload.unresolvedVariables ? (
            <Banner variant="warning" className="form-form-alert">
              {todoWorklistLabels.manualMailUnresolvedVariables}
            </Banner>
          ) : null}
          {previewStale ? (
            <Banner variant="warning" className="form-form-alert">
              {todoWorklistLabels.manualMailPreviewStale}
            </Banner>
          ) : null}

          <FormSection title={todoWorklistLabels.manualMailPreviewSection}>
            <div className="mail-template-preview-output">
              {previewPayload.templateName ? (
                <div className="mail-template-preview-block">
                  <h4>{todoWorklistLabels.manualMailPreviewTemplate}</h4>
                  <pre className="mail-template-preview-text">{previewPayload.templateName}</pre>
                </div>
              ) : null}
              <div className="mail-template-preview-block">
                <h4>{todoWorklistLabels.manualMailPreviewRecipients}</h4>
                <pre className="mail-template-preview-text">
                  {previewPayload.recipients.join("; ")}
                </pre>
              </div>
              <div className="mail-template-preview-block">
                <h4>{todoWorklistLabels.manualMailPreviewSmtp}</h4>
                <pre className="mail-template-preview-text">{previewPayload.smtpAccountName}</pre>
              </div>
              <div className="mail-template-preview-block">
                <h4>{todoWorklistLabels.manualMailPreviewSubject}</h4>
                <pre className="mail-template-preview-text">{previewPayload.subject}</pre>
              </div>
              <div className="mail-template-preview-block">
                <h4>{todoWorklistLabels.manualMailPreviewBody}</h4>
                <iframe
                  className="mail-template-html-preview"
                  title={todoWorklistLabels.manualMailPreviewBody}
                  sandbox=""
                  srcDoc={previewPayload.htmlDocument}
                />
              </div>
            </div>
          </FormSection>

          <div className="form-actions span-2">
            <button
              type="button"
              className="btn secondary"
              onClick={() => setStep("compose")}
              disabled={sending}
            >
              {todoWorklistLabels.manualMailPreviewBack}
            </button>
            <button
              type="button"
              className="btn primary"
              disabled={!canSendFromPreview}
              onClick={() => void handleSendFromPreview()}
            >
              {sending ? todoWorklistLabels.manualMailSending : todoWorklistLabels.manualMailSend}
            </button>
          </div>
        </div>
      ) : (
        <form
          className="manual-task-mail-form crm-form crm-form--standard"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}
          {success ? <Banner variant="success" className="form-form-alert">{success}</Banner> : null}
          {!previewSnapshot || previewStale ? (
            <Banner variant="info" className="form-form-alert">
              {previewStale && previewSnapshot
                ? todoWorklistLabels.manualMailPreviewStale
                : todoWorklistLabels.manualMailPreviewRequired}
            </Banner>
          ) : null}

          <FormSection title={todoWorklistLabels.manualMailRecipientsSection}>
            <FormGrid>
              <FormField
                label={todoWorklistLabels.manualMailRecipientPicker}
                htmlFor="manual-mail-recipient-picker"
                fullWidth
              >
                <SelectInput
                  id="manual-mail-recipient-picker"
                  value={pickerValue}
                  onChange={(event) => handlePickerChange(event.target.value)}
                  disabled={sending || previewing}
                >
                  <option value="">{todoWorklistLabels.manualMailRecipientPlaceholder}</option>
                  {recipientOptions.map((option) => (
                    <option
                      key={option.value}
                      value={option.value}
                      disabled={recipients.includes(option.value)}
                    >
                      {option.label}
                    </option>
                  ))}
                </SelectInput>
              </FormField>

              <FormField
                label={todoWorklistLabels.manualMailManualAdd}
                htmlFor="manual-mail-manual-email"
                fullWidth
                error={manualEmailError}
              >
                <div className="manual-task-mail-add-row">
                  <TextInput
                    id="manual-mail-manual-email"
                    type="text"
                    value={manualEmail}
                    onChange={(event) => {
                      setManualEmail(event.target.value);
                      setManualEmailError(null);
                    }}
                    placeholder={todoWorklistLabels.manualMailManualPlaceholder}
                    disabled={sending || previewing}
                    onKeyDown={handleManualEmailKeyDown}
                    aria-invalid={manualEmailError ? true : undefined}
                  />
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={handleAddManualEmail}
                    disabled={sending || previewing || !manualEmail.trim()}
                  >
                    {todoWorklistLabels.manualMailAddRecipient}
                  </button>
                </div>
              </FormField>

              <FormField label={todoWorklistLabels.manualMailRecipientsList} fullWidth>
                {recipients.length === 0 ? (
                  <p className="field-hint">{todoWorklistLabels.manualMailNoRecipients}</p>
                ) : (
                  <ul className="manual-task-mail-recipient-list">
                    {recipients.map((email) => (
                      <li key={email} className="manual-task-mail-recipient-item">
                        <span>{email}</span>
                        <IconButton
                          label={todoWorklistLabels.manualMailRemoveRecipient}
                          icon={<NavIconClose />}
                          disabled={sending || previewing}
                          onClick={() => {
                            setRecipients((current) => current.filter((item) => item !== email));
                            invalidatePreview();
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </FormField>
            </FormGrid>
          </FormSection>

          <FormSection title={todoWorklistLabels.manualMailContentSection}>
            <FormGrid>
              <FormField
                label={todoWorklistLabels.manualMailSmtpAccount}
                htmlFor="manual-mail-smtp"
                required
              >
                <SelectInput
                  id="manual-mail-smtp"
                  value={smtpAccountId}
                  onChange={(event) => {
                    setSmtpAccountId(event.target.value);
                    invalidatePreview();
                  }}
                  disabled={sending || previewing}
                  required
                >
                  <option value="">{todoWorklistLabels.manualMailSmtpPlaceholder}</option>
                  {smtpAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                      {account.is_default ? ` (${adminLabels.smtpDefaultBadge})` : ""}
                    </option>
                  ))}
                </SelectInput>
              </FormField>

              <FormField
                label={todoWorklistLabels.manualMailTemplate}
                htmlFor="manual-mail-template"
              >
                <SelectInput
                  id="manual-mail-template"
                  value={templateId}
                  onChange={(event) => handleTemplateChange(event.target.value)}
                  disabled={sending || previewing}
                >
                  <option value="">{todoWorklistLabels.manualMailTemplatePlaceholder}</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {formatMailTemplateOptionLabel(
                        template,
                        adminLabels.mailTemplatesDefaultBadge,
                      )}
                    </option>
                  ))}
                </SelectInput>
              </FormField>

              <FormField
                label={todoWorklistLabels.manualMailSubject}
                htmlFor="manual-mail-subject"
                required
                fullWidth
              >
                <TextInput
                  id="manual-mail-subject"
                  value={subject}
                  onChange={(event) => {
                    setSubject(event.target.value);
                    setSubjectTouched(true);
                    invalidatePreview();
                  }}
                  disabled={sending || previewing}
                  required
                />
              </FormField>

              <FormField
                label={todoWorklistLabels.manualMailBody}
                htmlFor="manual-mail-body"
                required
                fullWidth
              >
                <TextareaInput
                  id="manual-mail-body"
                  value={body}
                  onChange={(event) => {
                    setBody(event.target.value);
                    setBodyTouched(true);
                    invalidatePreview();
                  }}
                  rows={8}
                  disabled={sending || previewing}
                  required
                />
              </FormField>
            </FormGrid>
          </FormSection>

          <div className="form-actions span-2">
            <button
              type="button"
              className="btn secondary"
              onClick={requestClose}
              disabled={sending || previewing}
            >
              {todoLabels.cancel}
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={!canPreview}
              onClick={() => void handlePreview()}
            >
              {previewing
                ? todoWorklistLabels.manualMailPreviewRunning
                : todoWorklistLabels.manualMailPreviewAction}
            </button>
            <button type="button" className="btn primary" disabled title={todoWorklistLabels.manualMailPreviewRequired}>
              {todoWorklistLabels.manualMailSend}
            </button>
          </div>
        </form>
      )}
    </FormModal>
  );
}
