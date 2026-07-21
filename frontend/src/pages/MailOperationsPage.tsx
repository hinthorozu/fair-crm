import React from "react";
import { listFairs } from "../api/fairs";
import { ApiError, listMailOperations, retryMailOperation } from "../api/mailOperations";
import { ApiError as SmtpApiError, listSmtpAccounts } from "../api/smtp";
import { MailOperationActionsMenu } from "../components/mail_operations/MailOperationActionsMenu";
import { MailOperationDetailModal } from "../components/mail_operations/MailOperationDetailModal";
import { MailOperationErrorModal } from "../components/mail_operations/MailOperationErrorModal";
import { MailOperationLogsModal } from "../components/mail_operations/MailOperationLogsModal";
import { Badge } from "../components/ui/Badge";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { FilterPanel } from "../components/ui/FilterPanel";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { FormField, SelectInput, TextInput } from "../components/ui/form";
import { adminLabels } from "../labels/adminLabels";
import { fairLabels } from "../labels/fairLabels";
import type { Fair } from "../types/fair";
import type { MailOperationRecord, MailOperationSourceType, MailOperationStatus } from "../types/mailOperations";
import type { SmtpAccount } from "../types/smtp";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";
import {
  buildMailOperationSummary,
  formatMailOperationDateTime,
  mailOperationSourceLabel,
  mailOperationStatusLabel,
  mailOperationStatusVariant,
} from "../utils/mailOperations";

const MAIL_OPERATION_STATUS_OPTIONS: { value: MailOperationStatus | "all"; label: string }[] = [
  { value: "all", label: adminLabels.mailOperationsFilterAll },
  { value: "queued", label: adminLabels.mailOperationsStatusLabels.queued },
  { value: "sending", label: adminLabels.mailOperationsStatusLabels.sending },
  { value: "sent", label: adminLabels.mailOperationsStatusLabels.sent },
  { value: "failed", label: adminLabels.mailOperationsStatusLabels.failed },
  { value: "cancelled", label: adminLabels.mailOperationsStatusLabels.cancelled },
  { value: "skipped", label: adminLabels.mailOperationsStatusLabels.skipped },
];

const MAIL_OPERATION_SOURCE_OPTIONS: { value: MailOperationSourceType | "all"; label: string }[] = [
  { value: "all", label: adminLabels.mailOperationsFilterAll },
  { value: "smtp_test", label: adminLabels.mailOperationsSourceLabels.smtp_test },
  { value: "template_test", label: adminLabels.mailOperationsSourceLabels.template_test },
  { value: "fair_bulk_email", label: adminLabels.mailOperationsSourceLabels.fair_bulk_email },
  { value: "system_notification", label: adminLabels.mailOperationsSourceLabels.system_notification },
  { value: "manual_email", label: adminLabels.mailOperationsSourceLabels.manual_email },
  { value: "manual_task_mail", label: adminLabels.mailOperationsSourceLabels.manual_task_mail },
];

type DialogState =
  | { type: "detail"; record: MailOperationRecord }
  | { type: "logs"; record: MailOperationRecord }
  | { type: "error"; record: MailOperationRecord }
  | { type: "retry"; record: MailOperationRecord }
  | { type: "cancel"; record: MailOperationRecord }
  | null;

export function MailOperationsPage() {
  const [items, setItems] = React.useState<MailOperationRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [status, setStatus] = React.useState<MailOperationStatus | "all">("all");
  const [sourceType, setSourceType] = React.useState<MailOperationSourceType | "all">("all");
  const [smtpAccount, setSmtpAccount] = React.useState("all");
  const [fair, setFair] = React.useState("all");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [dialog, setDialog] = React.useState<DialogState>(null);
  const [toast, setToast] = React.useState<string | null>(null);
  const [smtpAccounts, setSmtpAccounts] = React.useState<SmtpAccount[]>([]);
  const [smtpAccountsLoading, setSmtpAccountsLoading] = React.useState(true);
  const [smtpAccountsError, setSmtpAccountsError] = React.useState<string | null>(null);
  const [fairs, setFairs] = React.useState<Fair[]>([]);
  const [fairsLoading, setFairsLoading] = React.useState(true);
  const [fairsError, setFairsError] = React.useState<string | null>(null);
  const [retryingId, setRetryingId] = React.useState<string | null>(null);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  React.useEffect(() => {
    let cancelled = false;
    setSmtpAccountsLoading(true);
    setSmtpAccountsError(null);

    void (async () => {
      try {
        const response = await listSmtpAccounts();
        if (cancelled) return;
        setSmtpAccounts(response.items);
      } catch (err) {
        if (cancelled) return;
        setSmtpAccounts([]);
        setSmtpAccountsError(err instanceof SmtpApiError ? err.message : adminLabels.smtpLoadError);
      } finally {
        if (!cancelled) setSmtpAccountsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    setFairsLoading(true);
    setFairsError(null);

    void (async () => {
      try {
        const response = await listFairs({ page: 1, pageSize: 100 });
        if (cancelled) return;
        setFairs(response.items);
      } catch (err) {
        if (cancelled) return;
        setFairs([]);
        setFairsError(err instanceof ApiError ? err.message : fairLabels.loadError);
      } finally {
        if (!cancelled) setFairsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    if (smtpAccount === "all") return;
    if (!smtpAccounts.some((account) => account.id === smtpAccount)) {
      setSmtpAccount("all");
    }
  }, [smtpAccount, smtpAccounts]);

  React.useEffect(() => {
    if (fair === "all") return;
    if (!fairs.some((item) => item.id === fair)) {
      setFair("all");
    }
  }, [fair, fairs]);

  const loadOperations = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listMailOperations({
        page: 1,
        pageSize: 100,
        search: debouncedSearch,
        status,
        sourceType,
        smtpAccountId: smtpAccount,
        fairId: fair,
        dateFrom,
        dateTo,
      });
      setItems(response.items);
    } catch (err) {
      setItems([]);
      setError(err instanceof ApiError ? err.message : adminLabels.mailOperationsLoadError);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, status, sourceType, smtpAccount, fair, dateFrom, dateTo]);

  React.useEffect(() => {
    void loadOperations();
  }, [loadOperations]);

  const showToast = React.useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  }, []);

  const handleRetryConfirm = React.useCallback(async () => {
    if (dialog?.type !== "retry") return;
    const record = dialog.record;
    setRetryingId(record.id);
    try {
      const result = await retryMailOperation(record.id);
      setDialog(null);
      await loadOperations();
      showToast(
        result.success
          ? adminLabels.mailOperationsRetrySuccess
          : adminLabels.mailOperationsRetryFailed,
      );
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : adminLabels.mailOperationsRetryFailed);
    } finally {
      setRetryingId(null);
    }
  }, [dialog, loadOperations, showToast]);

  const handleCopy = React.useCallback(
    async (record: MailOperationRecord) => {
      const summary = buildMailOperationSummary(record);
      try {
        await navigator.clipboard.writeText(summary);
        showToast(adminLabels.mailOperationsCopySuccess);
      } catch {
        showToast(adminLabels.mailOperationsCopyError);
      }
    },
    [showToast],
  );

  const actionHandlers = React.useMemo(
    () => ({
      onDetail: (record: MailOperationRecord) => setDialog({ type: "detail", record }),
      onLogs: (record: MailOperationRecord) => setDialog({ type: "logs", record }),
      onCopy: (record: MailOperationRecord) => void handleCopy(record),
      onRetry: (record: MailOperationRecord) => setDialog({ type: "retry", record }),
      onErrorDetail: (record: MailOperationRecord) => setDialog({ type: "error", record }),
      onCancel: (record: MailOperationRecord) => setDialog({ type: "cancel", record }),
    }),
    [handleCopy],
  );

  const columns = React.useMemo<UniversalDataTableColumn<MailOperationRecord>[]>(
    () => [
      {
        key: "date",
        title: adminLabels.mailOperationsColDate,
        render: (record) => formatMailOperationDateTime(record.created_at),
      },
      {
        key: "source",
        title: adminLabels.mailOperationsColSource,
        render: (record) => mailOperationSourceLabel(record.source_type, record),
      },
      {
        key: "fair",
        title: adminLabels.mailOperationsColFair,
        render: (record) => record.fair_name ?? "—",
      },
      {
        key: "customer",
        title: adminLabels.mailOperationsColCustomer,
        render: (record) => record.customer_name ?? "—",
      },
      {
        key: "recipient",
        title: adminLabels.mailOperationsColRecipientEmail,
        render: (record) => record.recipient_email,
      },
      {
        key: "smtp",
        title: adminLabels.mailOperationsColSmtpAccount,
        render: (record) => record.smtp_account_name ?? "—",
      },
      {
        key: "template",
        title: adminLabels.mailOperationsColTemplate,
        render: (record) => record.template_name ?? "—",
      },
      {
        key: "subject",
        title: adminLabels.mailOperationsColSubject,
        render: (record) => record.subject,
      },
      {
        key: "status",
        title: adminLabels.mailOperationsColStatus,
        render: (record) => (
          <Badge variant={mailOperationStatusVariant(record.status)}>
            {mailOperationStatusLabel(record.status, record)}
          </Badge>
        ),
      },
      {
        key: "error",
        title: adminLabels.mailOperationsColError,
        render: (record) => (
          <span className="mail-operation-error-cell" title={record.error_message ?? undefined}>
            {record.error_message ?? "—"}
          </span>
        ),
      },
      {
        key: "actions",
        title: adminLabels.mailOperationsColActions,
        render: (record) => (
          <MailOperationActionsMenu
            record={record}
            retryDisabled={retryingId === record.id}
            {...actionHandlers}
          />
        ),
      },
    ],
    [actionHandlers, retryingId],
  );

  const detailRecord = dialog?.type === "detail" ? dialog.record : null;
  const logsRecord = dialog?.type === "logs" ? dialog.record : null;
  const errorRecord = dialog?.type === "error" ? dialog.record : null;

  return (
    <PageShell className="mail-operations-page">
      <PageHeader
        title={adminLabels.mailOperationsTitle}
        subtitle={adminLabels.mailOperationsSubtitle}
        actions={[
          {
            id: "export",
            label: adminLabels.mailOperationsExport,
            onClick: () => undefined,
            disabled: true,
            title: adminLabels.mailOperationsExportSoon,
          },
        ]}
      />

      {toast ? <Banner variant="success">{toast}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <FilterPanel className="mail-operations-filters">
        <FormField label={adminLabels.mailOperationsFilterSearch} htmlFor="mail-operations-search">
          <TextInput
            id="mail-operations-search"
            type="search"
            value={search}
            placeholder={adminLabels.mailOperationsFilterSearchPlaceholder}
            onChange={(event) => setSearch(event.target.value)}
          />
        </FormField>

        <FormField label={adminLabels.mailOperationsFilterStatus} htmlFor="mail-operations-status">
          <SelectInput
            id="mail-operations-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as MailOperationStatus | "all")}
          >
            {MAIL_OPERATION_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectInput>
        </FormField>

        <FormField label={adminLabels.mailOperationsFilterSource} htmlFor="mail-operations-source">
          <SelectInput
            id="mail-operations-source"
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value as MailOperationSourceType | "all")}
          >
            {MAIL_OPERATION_SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectInput>
        </FormField>

        <FormField
          label={adminLabels.mailOperationsFilterSmtp}
          htmlFor="mail-operations-smtp"
          hint={smtpAccountsLoading ? adminLabels.dataOpLoading : undefined}
          error={smtpAccountsError ?? undefined}
        >
          <SelectInput
            id="mail-operations-smtp"
            value={smtpAccount}
            disabled={smtpAccountsLoading}
            onChange={(event) => setSmtpAccount(event.target.value)}
          >
            <option value="all">{adminLabels.mailOperationsFilterAll}</option>
            {smtpAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </SelectInput>
        </FormField>

        <FormField
          label={adminLabels.mailOperationsFilterFair}
          htmlFor="mail-operations-fair"
          hint={fairsLoading ? adminLabels.dataOpLoading : undefined}
          error={fairsError ?? undefined}
        >
          <SelectInput
            id="mail-operations-fair"
            value={fair}
            disabled={fairsLoading}
            onChange={(event) => setFair(event.target.value)}
          >
            <option value="all">{adminLabels.mailOperationsFilterAll}</option>
            {fairs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </SelectInput>
        </FormField>

        <FormField label={adminLabels.mailOperationsFilterDateFrom} htmlFor="mail-operations-date-from">
          <TextInput
            id="mail-operations-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
        </FormField>

        <FormField label={adminLabels.mailOperationsFilterDateTo} htmlFor="mail-operations-date-to">
          <TextInput
            id="mail-operations-date-to"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
        </FormField>
      </FilterPanel>

      <UniversalDataTable
        items={items}
        columns={columns}
        rowKey={(row) => row.id}
        loading={loading}
        emptyState={
          <EmptyState
            title={adminLabels.mailOperationsEmptyTitle}
            description={adminLabels.mailOperationsEmptyDescription}
          />
        }
      />

      <MailOperationDetailModal record={detailRecord} onClose={() => setDialog(null)} />
      <MailOperationLogsModal record={logsRecord} onClose={() => setDialog(null)} />
      <MailOperationErrorModal record={errorRecord} onClose={() => setDialog(null)} />

      {dialog?.type === "retry" ? (
        <ConfirmDialog
          title={adminLabels.mailOperationsRetryTitle}
          message={adminLabels.mailOperationsRetryMessage}
          confirmLabel={adminLabels.mailOperationsActionLabels.retry}
          loading={retryingId === dialog.record.id}
          onConfirm={() => void handleRetryConfirm()}
          onCancel={() => {
            if (retryingId) return;
            setDialog(null);
          }}
        />
      ) : null}

      {dialog?.type === "cancel" ? (
        <ConfirmDialog
          title={adminLabels.mailOperationsCancelTitle}
          message={adminLabels.mailOperationsCancelMessage}
          confirmLabel={adminLabels.mailOperationsActionLabels.cancel}
          variant="danger"
          onConfirm={() => {
            showToast(adminLabels.mailOperationsCancelTodo);
            setDialog(null);
          }}
          onCancel={() => setDialog(null)}
        />
      ) : null}
    </PageShell>
  );
}
