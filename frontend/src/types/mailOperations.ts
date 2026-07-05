/** Central mail operations list types. */

export type MailOperationStatus = "queued" | "sending" | "sent" | "failed" | "cancelled";

export type MailOperationSourceType =
  | "smtp_test"
  | "template_test"
  | "fair_bulk_email"
  | "system_notification"
  | "manual_email";

export interface MailOperationLogEntry {
  time: string;
  event: string;
  message: string;
}

export interface MailOperationRecord {
  id: string;
  created_at: string;
  source_type: MailOperationSourceType;
  source_type_label: string;
  fair_id: string | null;
  fair_name: string | null;
  customer_id: string | null;
  customer_name: string | null;
  recipient_email: string;
  recipient_name: string | null;
  smtp_account_id: string | null;
  smtp_account_name: string | null;
  template_id: string | null;
  template_name: string | null;
  subject: string;
  status: MailOperationStatus;
  status_label: string;
  error_message: string | null;
  operation_logs: MailOperationLogEntry[];
  retry_count: number;
  priority: number;
  sent_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
}

export type MailOperationActionId =
  | "detail"
  | "logs"
  | "copy"
  | "retry"
  | "error_detail"
  | "cancel";

export interface ListMailOperationsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: MailOperationStatus | "all";
  sourceType?: MailOperationSourceType | "all";
  smtpAccountId?: string | "all";
  fairId?: string | "all";
  dateFrom?: string;
  dateTo?: string;
}
