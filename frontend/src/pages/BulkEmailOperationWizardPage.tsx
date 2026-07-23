import React from "react";
import { previewBulkEmailOperation, sendBulkEmailOperation } from "../api/bulkEmailOperation";
import { ApiError } from "../api/client";
import { getFair } from "../api/fairs";
import { listMailTemplates } from "../api/mailTemplates";
import { listSmtpAccounts } from "../api/smtp";
import { FairEntitySelect } from "../components/FairEntitySelect";
import { NavIconClose } from "../components/layout/NavIcons";
import { BulkEmailPreviewRecipientsTable } from "../components/operations/BulkEmailPreviewRecipientsTable";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { IconButton } from "../components/ui/IconButton";
import { LoadingState } from "../components/ui/LoadingState";
import {
  CheckboxField,
  FieldError,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormSection,
  RadioField,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { adminLabels } from "../labels/adminLabels";
import { fairLabels } from "../labels/fairLabels";
import { operationLabels, wizardStepLabels } from "../labels/operationLabels";
import {
  canPerformMailTemplateAction,
  getGrantedMailTemplatePermissions,
} from "../permissions/mailTemplatePermissions";
import type { BulkEmailOperationPreviewResponse } from "../types/bulkEmailOperation";
import type { MailTemplate } from "../types/mailTemplates";
import type { SmtpAccount } from "../types/smtp";
import {
  formatMailTemplateOptionLabel,
  resolveSubjectAfterPreview,
  selectActiveMailTemplates,
} from "../utils/mailTemplateForm";

interface BulkEmailOperationWizardPageProps {
  onCancel: () => void;
  onCreated?: (operationId: string) => void;
}

function newClientToken(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

type RecipientSourceType = "manual" | "fair_list";
type WizardStepId = "recipient_source" | "mail_settings" | "summary" | "send";

type SelectedFair = {
  id: string;
  name: string;
};

const DEFAULT_FAIR_OPTIONS = {
  includeCompanyEmails: true,
  includeContactEmails: true,
  skipNoEmail: true,
  excludeInactive: true,
  dedupeEmails: true,
};

const EMPTY_WIZARD_STATE = {
  sourceType: "" as RecipientSourceType | "",
  excelFileName: "",
  manualEmails: "",
  selectedFairIds: [] as string[],
  countryFilter: "",
  cityFilter: "",
  companyNameSearch: "",
  ...DEFAULT_FAIR_OPTIONS,
  templateId: "",
  smtpAccountId: "",
  subject: "",
};

const STEPS: Array<{ id: WizardStepId }> = [
  { id: "recipient_source" },
  { id: "mail_settings" },
  { id: "summary" },
  { id: "send" },
];

export function BulkEmailOperationWizardPage({
  onCancel,
  onCreated,
}: BulkEmailOperationWizardPageProps) {
  return (
    <FormDirtyHost onClose={onCancel}>
      <BulkEmailOperationWizardPageInner onCancel={onCancel} onCreated={onCreated} />
    </FormDirtyHost>
  );
}

function BulkEmailOperationWizardPageInner({
  onCancel,
  onCreated,
}: BulkEmailOperationWizardPageProps) {
  const requestLeave = useModalFormCancel(onCancel);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const mailSettingsLoadedRef = React.useRef(false);
  const previewRequestIdRef = React.useRef(0);
  const sendLockRef = React.useRef(false);

  const mailTemplatePermissions = React.useMemo(() => getGrantedMailTemplatePermissions(), []);
  const canReadMailTemplates = canPerformMailTemplateAction(mailTemplatePermissions, "read");

  const [stepIndex, setStepIndex] = React.useState(0);
  const [fieldError, setFieldError] = React.useState<string | null>(null);

  const [sourceType, setSourceType] = React.useState<RecipientSourceType | "">("");
  const [excelFile, setExcelFile] = React.useState<File | null>(null);
  const [manualEmails, setManualEmails] = React.useState("");
  const [fairPickerId, setFairPickerId] = React.useState("");
  const [selectedFairs, setSelectedFairs] = React.useState<SelectedFair[]>([]);
  const [fairAddError, setFairAddError] = React.useState<string | null>(null);
  const [countryFilter, setCountryFilter] = React.useState("");
  const [cityFilter, setCityFilter] = React.useState("");
  const [companyNameSearch, setCompanyNameSearch] = React.useState("");
  const [includeCompanyEmails, setIncludeCompanyEmails] = React.useState(
    DEFAULT_FAIR_OPTIONS.includeCompanyEmails,
  );
  const [includeContactEmails, setIncludeContactEmails] = React.useState(
    DEFAULT_FAIR_OPTIONS.includeContactEmails,
  );
  const [skipNoEmail, setSkipNoEmail] = React.useState(DEFAULT_FAIR_OPTIONS.skipNoEmail);
  const [excludeInactive, setExcludeInactive] = React.useState(
    DEFAULT_FAIR_OPTIONS.excludeInactive,
  );
  const [dedupeEmails, setDedupeEmails] = React.useState(DEFAULT_FAIR_OPTIONS.dedupeEmails);

  const [templates, setTemplates] = React.useState<MailTemplate[]>([]);
  const [smtpAccounts, setSmtpAccounts] = React.useState<SmtpAccount[]>([]);
  const [templatesLoading, setTemplatesLoading] = React.useState(false);
  const [mailSettingsError, setMailSettingsError] = React.useState<string | null>(null);
  const [templateId, setTemplateId] = React.useState("");
  const [smtpAccountId, setSmtpAccountId] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [subjectTouched, setSubjectTouched] = React.useState(false);

  const [preview, setPreview] = React.useState<BulkEmailOperationPreviewResponse | null>(null);
  const [previewing, setPreviewing] = React.useState(false);
  const [previewError, setPreviewError] = React.useState<string | null>(null);
  const [previewFingerprint, setPreviewFingerprint] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);
  const [sendError, setSendError] = React.useState<string | null>(null);

  const currentStep = STEPS[stepIndex] ?? STEPS[0];
  const selectedTemplate = templates.find((item) => item.id === templateId) ?? null;
  const selectedSmtp = smtpAccounts.find((item) => item.id === smtpAccountId) ?? null;

  const wizardValues = React.useMemo(
    () => ({
      sourceType,
      excelFileName: excelFile?.name ?? "",
      excelFileSize: excelFile?.size ?? 0,
      excelFileModified: excelFile?.lastModified ?? 0,
      manualEmails,
      selectedFairIds: selectedFairs.map((fair) => fair.id),
      countryFilter,
      cityFilter,
      companyNameSearch,
      includeCompanyEmails,
      includeContactEmails,
      skipNoEmail,
      excludeInactive,
      dedupeEmails,
      templateId,
      smtpAccountId,
      subject,
      subjectTouched,
    }),
    [
      sourceType,
      excelFile,
      manualEmails,
      selectedFairs,
      countryFilter,
      cityFilter,
      companyNameSearch,
      includeCompanyEmails,
      includeContactEmails,
      skipNoEmail,
      excludeInactive,
      dedupeEmails,
      templateId,
      smtpAccountId,
      subject,
      subjectTouched,
    ],
  );
  useReportFormDirty(wizardValues, EMPTY_WIZARD_STATE);

  const previewInputFingerprint = React.useMemo(
    () =>
      JSON.stringify({
        sourceType,
        excelFileName: excelFile?.name ?? "",
        excelFileSize: excelFile?.size ?? 0,
        excelFileModified: excelFile?.lastModified ?? 0,
        manualEmails,
        selectedFairIds: selectedFairs.map((fair) => fair.id),
        countryFilter,
        cityFilter,
        companyNameSearch,
        includeCompanyEmails,
        includeContactEmails,
        skipNoEmail,
        excludeInactive,
        dedupeEmails,
        templateId,
        smtpAccountId,
        subjectTouched,
        subject: subjectTouched ? subject : "",
      }),
    [
      sourceType,
      excelFile,
      manualEmails,
      selectedFairs,
      countryFilter,
      cityFilter,
      companyNameSearch,
      includeCompanyEmails,
      includeContactEmails,
      skipNoEmail,
      excludeInactive,
      dedupeEmails,
      templateId,
      smtpAccountId,
      subject,
      subjectTouched,
    ],
  );

  const previewStale =
    Boolean(preview) &&
    previewFingerprint !== null &&
    previewFingerprint !== previewInputFingerprint;

  // Step 2 entry only: load templates + SMTP once; keep selections when returning.
  React.useEffect(() => {
    if (currentStep.id !== "mail_settings") return;
    if (mailSettingsLoadedRef.current) return;

    let cancelled = false;

    if (!canReadMailTemplates) {
      setTemplates([]);
      setSmtpAccounts([]);
      setMailSettingsError(fairLabels.bulkEmailTemplateReadDenied);
      setTemplatesLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setTemplatesLoading(true);
    setMailSettingsError(null);

    void (async () => {
      try {
        const [templateResponse, smtpResponse] = await Promise.all([
          listMailTemplates(),
          listSmtpAccounts(),
        ]);
        if (cancelled) return;

        const activeTemplates = selectActiveMailTemplates(templateResponse.items);
        const activeSmtp = smtpResponse.items.filter((item) => item.is_active);
        setTemplates(activeTemplates);
        setSmtpAccounts(activeSmtp);

        if (activeTemplates.length === 0) {
          setMailSettingsError(fairLabels.bulkEmailNoTemplates);
        } else {
          const defaultTemplate =
            activeTemplates.find((item) => item.is_default) ?? activeTemplates[0] ?? null;
          setTemplateId((current) => current || defaultTemplate?.id || "");
          if (defaultTemplate) {
            setSubject((current) => (current.trim() ? current : defaultTemplate.subject));
          }
        }

        setSmtpAccountId((current) => {
          if (current) return current;
          const defaultSmtp =
            activeSmtp.find((item) => item.is_default) ?? activeSmtp[0] ?? null;
          return defaultSmtp?.id ?? "";
        });

        mailSettingsLoadedRef.current = true;
      } catch (err) {
        if (!cancelled) {
          setTemplates([]);
          setSmtpAccounts([]);
          setMailSettingsError(
            err instanceof ApiError ? err.message : fairLabels.bulkEmailLoadTemplatesError,
          );
        }
      } finally {
        if (!cancelled) setTemplatesLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [canReadMailTemplates, currentStep.id]);

  React.useEffect(() => {
    if (currentStep.id !== "mail_settings") return;
    if (selectedTemplate && !subjectTouched) {
      setSubject(selectedTemplate.subject);
    }
  }, [currentStep.id, selectedTemplate, subjectTouched]);

  // Step 3 entry: build real recipient + mail preview (no send).
  React.useEffect(() => {
    if (currentStep.id !== "summary") return;
    if (!sourceType || !templateId || !smtpAccountId) return;
    if (preview && !previewStale && previewFingerprint === previewInputFingerprint) return;

    let cancelled = false;
    const requestId = ++previewRequestIdRef.current;
    setPreviewing(true);
    setPreviewError(null);
    setPreview(null);

    void (async () => {
      try {
        const result = await previewBulkEmailOperation({
          source_type: sourceType,
          template_id: templateId,
          smtp_account_id: smtpAccountId,
          subject_override: subjectTouched ? subject.trim() : null,
          manual_emails: sourceType === "manual" ? manualEmails : null,
          excel_file: sourceType === "manual" ? excelFile : null,
          fair_ids: sourceType === "fair_list" ? selectedFairs.map((fair) => fair.id) : [],
          country_filter: sourceType === "fair_list" ? countryFilter.trim() || null : null,
          city_filter: sourceType === "fair_list" ? cityFilter.trim() || null : null,
          company_name_contains:
            sourceType === "fair_list" ? companyNameSearch.trim() || null : null,
          recipient_options: {
            include_customer_emails: includeCompanyEmails,
            include_contact_emails: includeContactEmails,
            skip_no_email: skipNoEmail,
            exclude_inactive: excludeInactive,
            dedupe_emails: dedupeEmails,
          },
        });
        if (cancelled || requestId !== previewRequestIdRef.current) return;
        setPreview(result);
        setPreviewFingerprint(previewInputFingerprint);
        setSubject((current) =>
          resolveSubjectAfterPreview(current, result.mail.rendered_subject, subjectTouched),
        );
      } catch (err) {
        if (cancelled || requestId !== previewRequestIdRef.current) return;
        setPreview(null);
        setPreviewFingerprint(null);
        setPreviewError(
          err instanceof ApiError ? err.message : operationLabels.bulkEmailPreviewError,
        );
      } finally {
        if (!cancelled && requestId === previewRequestIdRef.current) {
          setPreviewing(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // Intentionally keyed by step + fingerprint; other deps are embedded in fingerprint.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep.id, previewInputFingerprint]);

  const resetManualForm = () => {
    setExcelFile(null);
    setManualEmails("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const resetFairForm = () => {
    setFairPickerId("");
    setSelectedFairs([]);
    setFairAddError(null);
    setCountryFilter("");
    setCityFilter("");
    setCompanyNameSearch("");
    setIncludeCompanyEmails(DEFAULT_FAIR_OPTIONS.includeCompanyEmails);
    setIncludeContactEmails(DEFAULT_FAIR_OPTIONS.includeContactEmails);
    setSkipNoEmail(DEFAULT_FAIR_OPTIONS.skipNoEmail);
    setExcludeInactive(DEFAULT_FAIR_OPTIONS.excludeInactive);
    setDedupeEmails(DEFAULT_FAIR_OPTIONS.dedupeEmails);
  };

  const invalidatePreview = () => {
    previewRequestIdRef.current += 1;
    setPreview(null);
    setPreviewError(null);
    setPreviewFingerprint(null);
    setPreviewing(false);
  };

  const handleSourceTypeChange = (next: string) => {
    const typed = next as RecipientSourceType;
    setSourceType(typed);
    setFieldError(null);
    invalidatePreview();
    if (typed === "manual") {
      resetFairForm();
    } else {
      resetManualForm();
    }
  };

  const handleFairPickerChange = (nextId: string) => {
    setFairPickerId(nextId);
    setFairAddError(null);
    setFieldError(null);
    if (!nextId) return;

    if (selectedFairs.some((fair) => fair.id === nextId)) {
      setFairAddError(operationLabels.bulkEmailFairAlreadySelected);
      setFairPickerId("");
      return;
    }

    void getFair(nextId)
      .then((fair) => {
        setSelectedFairs((current) => {
          if (current.some((item) => item.id === fair.id)) return current;
          return [...current, { id: fair.id, name: fair.name }];
        });
        setFairPickerId("");
        invalidatePreview();
      })
      .catch(() => {
        setFairPickerId("");
      });
  };

  const canProceedRecipientSource = (() => {
    if (!sourceType) return false;
    if (sourceType === "manual") {
      return Boolean(excelFile) || Boolean(manualEmails.trim());
    }
    return selectedFairs.length > 0;
  })();

  const canProceedMailSettings =
    !templatesLoading &&
    Boolean(templateId.trim()) &&
    Boolean(smtpAccountId.trim()) &&
    Boolean(subject.trim()) &&
    !mailSettingsError;

  const previewReady =
    Boolean(preview) &&
    !previewing &&
    !previewStale &&
    !previewError &&
    previewFingerprint === previewInputFingerprint;

  const canProceedSummary =
    previewReady && (preview?.recipients.deduped_recipient_count ?? 0) > 0;

  const canProceed =
    currentStep.id === "recipient_source"
      ? canProceedRecipientSource
      : currentStep.id === "mail_settings"
        ? canProceedMailSettings
        : currentStep.id === "summary"
          ? canProceedSummary
          : false;

  const showContinue =
    currentStep.id === "recipient_source" ||
    currentStep.id === "mail_settings" ||
    currentStep.id === "summary";

  const validateCurrentStep = (): boolean => {
    if (currentStep.id === "recipient_source") {
      if (!sourceType) {
        setFieldError(operationLabels.bulkEmailSourceRequired);
        return false;
      }
      if (sourceType === "manual") {
        if (!excelFile && !manualEmails.trim()) {
          setFieldError(operationLabels.bulkEmailManualSourceRequired);
          return false;
        }
      } else if (selectedFairs.length === 0) {
        setFieldError(operationLabels.bulkEmailFairSourceRequired);
        return false;
      }
    }
    if (currentStep.id === "mail_settings") {
      if (templatesLoading) return false;
      if (mailSettingsError) {
        setFieldError(mailSettingsError);
        return false;
      }
      if (!templateId.trim()) {
        setFieldError(operationLabels.bulkEmailTemplateRequired);
        return false;
      }
      if (!smtpAccountId.trim()) {
        setFieldError(operationLabels.bulkEmailSmtpRequired);
        return false;
      }
      if (!subject.trim()) {
        setFieldError(operationLabels.bulkEmailSubjectRequired);
        return false;
      }
    }
    if (currentStep.id === "summary") {
      if (previewing) return false;
      if (!previewReady) {
        setFieldError(previewError ?? operationLabels.bulkEmailPreviewError);
        return false;
      }
      if ((preview?.recipients.deduped_recipient_count ?? 0) === 0) {
        setFieldError(operationLabels.bulkEmailPreviewCannotContinue);
        return false;
      }
    }
    setFieldError(null);
    return true;
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    if (currentStep.id === "mail_settings") {
      setPreview(null);
      setPreviewError(null);
      setPreviewFingerprint(null);
      setPreviewing(true);
    }
    setStepIndex((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const goBack = () => {
    setFieldError(null);
    setSendError(null);
    setStepIndex((prev) => Math.max(prev - 1, 0));
  };

  const handleTemplateChange = (nextId: string) => {
    setTemplateId(nextId);
    setSubjectTouched(false);
    setFieldError(null);
    invalidatePreview();
  };

  const handleSubjectChange = (value: string) => {
    setSubject(value);
    setSubjectTouched(true);
    setFieldError(null);
    invalidatePreview();
  };

  const handleSend = async () => {
    if (sendLockRef.current || sending) return;
    if (!sourceType || !templateId || !smtpAccountId || !subject.trim()) {
      setSendError(operationLabels.bulkEmailSendError);
      return;
    }
    if (!previewReady || (preview?.recipients.deduped_recipient_count ?? 0) === 0) {
      setSendError(operationLabels.bulkEmailPreviewCannotContinue);
      return;
    }

    sendLockRef.current = true;
    setSending(true);
    setSendError(null);
    setFieldError(null);
    const clientToken = newClientToken();

    try {
      const result = await sendBulkEmailOperation({
        source_type: sourceType,
        template_id: templateId,
        smtp_account_id: smtpAccountId,
        subject: subject.trim(),
        title: null,
        manual_emails: sourceType === "manual" ? manualEmails : null,
        excel_file: sourceType === "manual" ? excelFile : null,
        fair_ids: sourceType === "fair_list" ? selectedFairs.map((fair) => fair.id) : [],
        country_filter: sourceType === "fair_list" ? countryFilter.trim() || null : null,
        city_filter: sourceType === "fair_list" ? cityFilter.trim() || null : null,
        company_name_contains:
          sourceType === "fair_list" ? companyNameSearch.trim() || null : null,
        recipient_options: {
          include_customer_emails: includeCompanyEmails,
          include_contact_emails: includeContactEmails,
          skip_no_email: skipNoEmail,
          exclude_inactive: excludeInactive,
          dedupe_emails: dedupeEmails,
        },
        client_token: clientToken,
      });
      onCreated?.(result.operation_id);
    } catch (err) {
      sendLockRef.current = false;
      setSendError(err instanceof ApiError ? err.message : operationLabels.bulkEmailSendError);
    } finally {
      setSending(false);
    }
  };

  const navDisabled = templatesLoading || previewing || sending;

  return (
    <PageShell className="operation-wizard bulk-email-operation-wizard">
      <PageHeader
        title={operationLabels.bulkEmailWizardTitle}
        subtitle={operationLabels.bulkEmailWizardSubtitle}
        breadcrumbs={[
          { label: operationLabels.pageTitle, onClick: requestLeave },
          { label: operationLabels.bulkEmailWizardTitle, current: true },
        ]}
      />

      <div className="wizard-stepper" aria-label="Wizard adımları">
        {STEPS.map((step, index) => (
          <span
            key={step.id}
            className={`wizard-step ${
              index === stepIndex ? "active" : index < stepIndex ? "done" : ""
            }`}
          >
            {index + 1}. {wizardStepLabels[step.id] ?? step.id}
          </span>
        ))}
      </div>

      <Card>
        {currentStep.id === "recipient_source" ? (
          <>
            <FormSection title={operationLabels.stepRecipientSource}>
              <FormField label={operationLabels.bulkEmailSourceTypeLabel} required fullWidth>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-3)",
                  }}
                >
                  <RadioField
                    id="bulk-email-source-manual"
                    name="bulk-email-recipient-source"
                    label={operationLabels.bulkEmailSourceManual}
                    value="manual"
                    checked={sourceType === "manual"}
                    onChange={handleSourceTypeChange}
                  />
                  <RadioField
                    id="bulk-email-source-fair-list"
                    name="bulk-email-recipient-source"
                    label={operationLabels.bulkEmailSourceFairList}
                    value="fair_list"
                    checked={sourceType === "fair_list"}
                    onChange={handleSourceTypeChange}
                  />
                </div>
              </FormField>
            </FormSection>

            {sourceType === "manual" ? (
              <FormSection title={operationLabels.bulkEmailSourceManual}>
                <FormGrid>
                  <FormField
                    label={operationLabels.bulkEmailExcelLabel}
                    htmlFor="bulk-email-excel-file"
                    fullWidth
                    hint={operationLabels.bulkEmailExcelHint}
                  >
                    <TextInput
                      ref={fileInputRef}
                      id="bulk-email-excel-file"
                      type="file"
                      accept=".xlsx"
                      hidden
                      onChange={(event) => {
                        setExcelFile(event.target.files?.[0] ?? null);
                        setFieldError(null);
                        invalidatePreview();
                      }}
                    />
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        alignItems: "center",
                        gap: "var(--space-3)",
                      }}
                    >
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        {operationLabels.bulkEmailExcelSelect}
                      </Button>
                      {excelFile ? <span>{excelFile.name}</span> : null}
                    </div>
                  </FormField>

                  <FormField
                    label={operationLabels.bulkEmailManualEmailsLabel}
                    htmlFor="bulk-email-manual-emails"
                    fullWidth
                    hint={operationLabels.bulkEmailManualEmailsHint}
                  >
                    <TextareaInput
                      id="bulk-email-manual-emails"
                      value={manualEmails}
                      onChange={(event) => {
                        setManualEmails(event.target.value);
                        setFieldError(null);
                        invalidatePreview();
                      }}
                      rows={4}
                      placeholder={operationLabels.bulkEmailManualEmailsPlaceholder}
                    />
                  </FormField>
                </FormGrid>
              </FormSection>
            ) : null}

            {sourceType === "fair_list" ? (
              <>
                <FormSection title={operationLabels.bulkEmailSourceFairList}>
                  <FormGrid>
                    <FormField
                      label={operationLabels.bulkEmailFairSelectLabel}
                      htmlFor="bulk-email-fair-picker"
                      required
                      fullWidth
                      hint={operationLabels.bulkEmailFairSelectHint}
                      error={fairAddError ?? undefined}
                    >
                      <FairEntitySelect
                        id="bulk-email-fair-picker"
                        value={fairPickerId}
                        onChange={handleFairPickerChange}
                        allowClear
                      />
                    </FormField>

                    <FormField label={operationLabels.bulkEmailFairSelectedLabel} fullWidth>
                      {selectedFairs.length === 0 ? (
                        <p className="field-hint">{operationLabels.bulkEmailFairSelectedEmpty}</p>
                      ) : (
                        <ul className="selected-entity-list">
                          {selectedFairs.map((fair) => (
                            <li key={fair.id} className="selected-entity-item">
                              <span>{fair.name}</span>
                              <IconButton
                                label={operationLabels.bulkEmailFairRemove}
                                icon={<NavIconClose />}
                                onClick={() => {
                                  setSelectedFairs((current) =>
                                    current.filter((item) => item.id !== fair.id),
                                  );
                                  setFieldError(null);
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

                <FormSection title={operationLabels.bulkEmailFiltersSection}>
                  <FormGrid>
                    <FormField
                      label={operationLabels.bulkEmailCountryFilterLabel}
                      htmlFor="bulk-email-country-filter"
                    >
                      <TextInput
                        id="bulk-email-country-filter"
                        value={countryFilter}
                        onChange={(event) => {
                          setCountryFilter(event.target.value);
                          invalidatePreview();
                        }}
                      />
                    </FormField>
                    <FormField
                      label={operationLabels.bulkEmailCityFilterLabel}
                      htmlFor="bulk-email-city-filter"
                    >
                      <TextInput
                        id="bulk-email-city-filter"
                        value={cityFilter}
                        onChange={(event) => {
                          setCityFilter(event.target.value);
                          invalidatePreview();
                        }}
                      />
                    </FormField>
                    <FormField
                      label={operationLabels.bulkEmailCompanyNameSearchLabel}
                      htmlFor="bulk-email-company-search"
                      fullWidth
                    >
                      <TextInput
                        id="bulk-email-company-search"
                        value={companyNameSearch}
                        onChange={(event) => {
                          setCompanyNameSearch(event.target.value);
                          invalidatePreview();
                        }}
                      />
                    </FormField>
                  </FormGrid>
                </FormSection>

                <FormSection title={operationLabels.bulkEmailRecipientOptionsSection}>
                  <div className="checkbox-list">
                    <CheckboxField
                      id="bulk-email-include-company-emails"
                      label={operationLabels.bulkEmailIncludeCompanyEmails}
                      checked={includeCompanyEmails}
                      onChange={(next) => {
                        setIncludeCompanyEmails(next);
                        invalidatePreview();
                      }}
                      className="checkbox-row"
                    />
                    <CheckboxField
                      id="bulk-email-include-contact-emails"
                      label={operationLabels.bulkEmailIncludeContactEmails}
                      checked={includeContactEmails}
                      onChange={(next) => {
                        setIncludeContactEmails(next);
                        invalidatePreview();
                      }}
                      className="checkbox-row"
                    />
                    <CheckboxField
                      id="bulk-email-skip-no-email"
                      label={operationLabels.bulkEmailSkipNoEmail}
                      checked={skipNoEmail}
                      onChange={(next) => {
                        setSkipNoEmail(next);
                        invalidatePreview();
                      }}
                      className="checkbox-row"
                    />
                    <CheckboxField
                      id="bulk-email-exclude-inactive"
                      label={operationLabels.bulkEmailExcludeInactive}
                      checked={excludeInactive}
                      onChange={(next) => {
                        setExcludeInactive(next);
                        invalidatePreview();
                      }}
                      className="checkbox-row"
                    />
                    <CheckboxField
                      id="bulk-email-dedupe-emails"
                      label={operationLabels.bulkEmailDedupeEmails}
                      checked={dedupeEmails}
                      onChange={(next) => {
                        setDedupeEmails(next);
                        invalidatePreview();
                      }}
                      className="checkbox-row"
                    />
                  </div>
                </FormSection>
              </>
            ) : null}
          </>
        ) : null}

        {currentStep.id === "mail_settings" ? (
          templatesLoading ? (
            <LoadingState />
          ) : (
            <FormSection title={operationLabels.stepMailSettings}>
              {mailSettingsError ? <Banner variant="error">{mailSettingsError}</Banner> : null}
              <FormGrid>
                <FormField
                  label={operationLabels.bulkEmailTemplateLabel}
                  htmlFor="bulk-email-template"
                  required
                  fullWidth
                >
                  <SelectInput
                    id="bulk-email-template"
                    value={templateId}
                    disabled={!canReadMailTemplates || templates.length === 0}
                    onChange={(event) => handleTemplateChange(event.target.value)}
                  >
                    <option value="">{operationLabels.bulkEmailTemplatePlaceholder}</option>
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
                  label={operationLabels.bulkEmailSmtpLabel}
                  htmlFor="bulk-email-smtp"
                  required
                  fullWidth
                >
                  <SelectInput
                    id="bulk-email-smtp"
                    value={smtpAccountId}
                    disabled={smtpAccounts.length === 0}
                    onChange={(event) => {
                      setSmtpAccountId(event.target.value);
                      setFieldError(null);
                      invalidatePreview();
                    }}
                  >
                    <option value="">{operationLabels.bulkEmailSmtpPlaceholder}</option>
                    {smtpAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                        {account.is_default
                          ? ` (${adminLabels.mailTemplatesDefaultBadge})`
                          : ""}
                      </option>
                    ))}
                  </SelectInput>
                </FormField>

                <FormField
                  label={operationLabels.bulkEmailSubjectLabel}
                  htmlFor="bulk-email-subject"
                  required
                  fullWidth
                >
                  <TextInput
                    id="bulk-email-subject"
                    value={subject}
                    onChange={(event) => handleSubjectChange(event.target.value)}
                    required
                  />
                </FormField>
              </FormGrid>
            </FormSection>
          )
        ) : null}

        {currentStep.id === "summary" ? (
          previewing ? (
            <LoadingState message={operationLabels.bulkEmailPreviewLoading} />
          ) : previewError ? (
            <Banner variant="error">{previewError}</Banner>
          ) : preview ? (
            <>
              <FormSection title={operationLabels.bulkEmailRecipientsSection}>
                <div className="detail-grid compact">
                  <div>
                    <strong>{operationLabels.bulkEmailSummarySource}</strong>
                    <div>
                      {preview.recipients.source_type === "manual"
                        ? operationLabels.bulkEmailSourceManual
                        : operationLabels.bulkEmailSourceFairList}
                    </div>
                  </div>
                  {preview.recipients.source_type === "manual" ? (
                    <>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryTotalFound}</strong>
                        <div>{preview.recipients.total_found ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryValidEmails}</strong>
                        <div>{preview.recipients.valid_email_count}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryDuplicates}</strong>
                        <div>{preview.recipients.duplicate_count ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryInvalid}</strong>
                        <div>{preview.recipients.invalid_count ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryDeduped}</strong>
                        <div>{preview.recipients.deduped_recipient_count}</div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryFairCount}</strong>
                        <div>{preview.recipients.selected_fair_count ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryFairNames}</strong>
                        <div>
                          {(preview.recipients.selected_fair_names ?? []).join(", ") || "—"}
                        </div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryCustomers}</strong>
                        <div>{preview.recipients.total_customers ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryContacts}</strong>
                        <div>{preview.recipients.total_contacts ?? 0}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryValidEmails}</strong>
                        <div>{preview.recipients.valid_email_count}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummaryDeduped}</strong>
                        <div>{preview.recipients.deduped_recipient_count}</div>
                      </div>
                      <div>
                        <strong>{operationLabels.bulkEmailSummarySkipped}</strong>
                        <div>{preview.recipients.skipped_count}</div>
                      </div>
                    </>
                  )}
                </div>

                {preview.recipients.recipients.length === 0 ? (
                  <EmptyState title={operationLabels.bulkEmailPreviewEmptyRecipients} />
                ) : (
                  <BulkEmailPreviewRecipientsTable
                    recipients={preview.recipients.recipients}
                    sourceType={preview.recipients.source_type}
                    dataVersion={previewFingerprint ?? previewInputFingerprint}
                  />
                )}

                {preview.recipients.deduped_recipient_count === 0 ? (
                  <Banner variant="warning">{operationLabels.bulkEmailPreviewCannotContinue}</Banner>
                ) : null}
              </FormSection>

              <FormSection title={operationLabels.bulkEmailMailSummarySection}>
                <div className="detail-grid compact">
                  <div>
                    <strong>{operationLabels.bulkEmailTemplateLabel}</strong>
                    <div>{preview.mail.template_name}</div>
                  </div>
                  <div>
                    <strong>{operationLabels.bulkEmailSmtpLabel}</strong>
                    <div>
                      {preview.mail.smtp_account_name ||
                        selectedSmtp?.name ||
                        preview.mail.smtp_account_id}
                    </div>
                  </div>
                  <div>
                    <strong>{operationLabels.bulkEmailSubjectLabel}</strong>
                    <div>{subject.trim() || preview.mail.rendered_subject}</div>
                  </div>
                </div>
              </FormSection>

              <FormSection title={operationLabels.bulkEmailMailContentSection}>
                <div className="mail-template-preview-block">
                  <h4>{operationLabels.bulkEmailSubjectLabel}</h4>
                  <pre className="mail-template-preview-text">
                    {subject.trim() || preview.mail.rendered_subject}
                  </pre>
                </div>
                {preview.mail.body_text ? (
                  <div className="mail-template-preview-block">
                    <h4>{adminLabels.mailTemplatesRenderedBodyText}</h4>
                    <pre className="mail-template-preview-text">{preview.mail.body_text}</pre>
                  </div>
                ) : null}
                {preview.mail.body_html ? (
                  <div className="mail-template-preview-block">
                    <h4>{adminLabels.mailTemplatesRenderedBodyHtml}</h4>
                    <iframe
                      className="mail-template-html-preview"
                      title={adminLabels.mailTemplatesRenderedBodyHtml}
                      sandbox=""
                      srcDoc={preview.mail.body_html}
                    />
                  </div>
                ) : null}
              </FormSection>
            </>
          ) : (
            <EmptyState title={operationLabels.bulkEmailPreviewEmptyRecipients} />
          )
        ) : null}

        {currentStep.id === "send" ? (
          <FormSection title={operationLabels.bulkEmailSendSummaryTitle}>
            {sendError ? <Banner variant="error">{sendError}</Banner> : null}
            <div className="detail-grid compact">
              <div>
                <strong>{operationLabels.bulkEmailSummarySource}</strong>
                <div>
                  {sourceType === "manual"
                    ? operationLabels.bulkEmailSourceManual
                    : operationLabels.bulkEmailSourceFairList}
                </div>
              </div>
              <div>
                <strong>{operationLabels.bulkEmailSummaryDeduped}</strong>
                <div>{preview?.recipients.deduped_recipient_count ?? 0}</div>
              </div>
              <div>
                <strong>{operationLabels.bulkEmailTemplateLabel}</strong>
                <div>
                  {preview?.mail.template_name ||
                    selectedTemplate?.name ||
                    templateId ||
                    "—"}
                </div>
              </div>
              <div>
                <strong>{operationLabels.bulkEmailSmtpLabel}</strong>
                <div>
                  {preview?.mail.smtp_account_name || selectedSmtp?.name || smtpAccountId || "—"}
                </div>
              </div>
              <div>
                <strong>{operationLabels.bulkEmailSubjectLabel}</strong>
                <div>{subject.trim() || preview?.mail.rendered_subject || "—"}</div>
              </div>
            </div>
          </FormSection>
        ) : null}

        {fieldError ? <FieldError>{fieldError}</FieldError> : null}

        <div className="wizard-nav">
          <Button type="button" variant="secondary" onClick={requestLeave} disabled={navDisabled}>
            {operationLabels.dismiss}
          </Button>
          {stepIndex > 0 ? (
            <Button type="button" variant="secondary" onClick={goBack} disabled={navDisabled}>
              {operationLabels.back}
            </Button>
          ) : null}
          {showContinue ? (
            <Button
              type="button"
              variant="primary"
              onClick={goNext}
              disabled={!canProceed || navDisabled}
            >
              {operationLabels.continue}
            </Button>
          ) : null}
          {currentStep.id === "send" ? (
            <Button
              type="button"
              variant="primary"
              onClick={() => void handleSend()}
              disabled={sending || !previewReady}
            >
              {sending ? operationLabels.bulkEmailSending : operationLabels.bulkEmailSendAction}
            </Button>
          ) : null}
        </div>
      </Card>
    </PageShell>
  );
}
