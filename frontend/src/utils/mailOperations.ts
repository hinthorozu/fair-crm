import type { BadgeVariant } from "../components/ui/Badge";
import { adminLabels } from "../labels/adminLabels";
import type {
  MailOperationActionId,
  MailOperationLogEntry,
  MailOperationRecord,
  MailOperationSourceType,
  MailOperationStatus,
} from "../types/mailOperations";

export function mailOperationStatusLabel(
  status: MailOperationStatus,
  record?: Pick<MailOperationRecord, "status_label">,
): string {
  return record?.status_label ?? adminLabels.mailOperationsStatusLabels[status] ?? status;
}

export function mailOperationStatusVariant(status: MailOperationStatus): BadgeVariant {
  switch (status) {
    case "sent":
      return "success";
    case "failed":
      return "danger";
    case "queued":
      return "info";
    case "sending":
      return "warning";
    case "cancelled":
      return "neutral";
    case "skipped":
      return "neutral";
    default:
      return "default";
  }
}

export function mailOperationSourceLabel(
  source: MailOperationSourceType,
  record?: Pick<MailOperationRecord, "source_type_label">,
): string {
  return record?.source_type_label ?? adminLabels.mailOperationsSourceLabels[source] ?? source;
}

export function getMailOperationActions(status: MailOperationStatus): MailOperationActionId[] {
  switch (status) {
    case "sent":
      return ["detail", "logs", "copy"];
    case "failed":
      return ["detail", "retry", "error_detail", "logs"];
    case "queued":
      return ["detail", "cancel", "logs"];
    case "sending":
      return ["detail", "logs"];
    case "cancelled":
      return ["detail", "logs"];
    case "skipped":
      return ["detail", "logs"];
    default:
      return ["detail", "logs"];
  }
}

export function mailOperationActionLabel(action: MailOperationActionId): string {
  return adminLabels.mailOperationsActionLabels[action];
}

export function formatMailOperationDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR");
}

export function formatMailOperationLogEntry(entry: MailOperationLogEntry): string {
  const time = entry.time ? formatMailOperationDateTime(entry.time) : "—";
  return `${time} [${entry.event}] ${entry.message}`;
}

export function buildMailOperationSummary(record: MailOperationRecord): string {
  const lines = [
    `${adminLabels.mailOperationsColDate}: ${formatMailOperationDateTime(record.created_at)}`,
    `${adminLabels.mailOperationsColSource}: ${mailOperationSourceLabel(record.source_type, record)}`,
    `${adminLabels.mailOperationsColFair}: ${record.fair_name ?? "—"}`,
    `${adminLabels.mailOperationsColCustomer}: ${record.customer_name ?? "—"}`,
    `${adminLabels.mailOperationsColRecipientEmail}: ${record.recipient_email}`,
    `${adminLabels.mailOperationsColSmtpAccount}: ${record.smtp_account_name ?? "—"}`,
    `${adminLabels.mailOperationsColTemplate}: ${record.template_name ?? "—"}`,
    `${adminLabels.mailOperationsColSubject}: ${record.subject}`,
    `${adminLabels.mailOperationsColStatus}: ${mailOperationStatusLabel(record.status, record)}`,
  ];
  if (record.error_message) {
    lines.push(`${adminLabels.mailOperationsColError}: ${record.error_message}`);
  }
  return lines.join("\n");
}
