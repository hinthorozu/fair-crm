export type BulkEmailOperationSourceType = "manual" | "fair_list";

export type BulkEmailOperationRecipientOptions = {
  include_customer_emails: boolean;
  include_contact_emails: boolean;
  skip_no_email: boolean;
  exclude_inactive: boolean;
  dedupe_emails: boolean;
};

export type BulkEmailOperationPreviewRecipient = {
  recipient_key: string;
  email: string;
  source: string;
  status: string;
  skip_reason: string | null;
  recipient_name: string | null;
  company_name: string | null;
  fair_id: string | null;
  fair_name: string | null;
  customer_id: string | null;
  contact_id: string | null;
  participation_id: string | null;
};

export type BulkEmailOperationRecipientSummary = {
  source_type: BulkEmailOperationSourceType;
  total_found: number | null;
  valid_email_count: number;
  duplicate_count: number | null;
  invalid_count: number | null;
  deduped_recipient_count: number;
  skipped_count: number;
  selected_fair_count: number | null;
  selected_fair_names: string[] | null;
  total_customers: number | null;
  total_contacts: number | null;
  recipients: BulkEmailOperationPreviewRecipient[];
};

export type BulkEmailOperationMailPreview = {
  template_id: string;
  template_name: string;
  smtp_account_id: string;
  smtp_account_name: string;
  rendered_subject: string;
  body_html: string | null;
  body_text: string | null;
};

export type BulkEmailOperationPreviewResponse = {
  recipients: BulkEmailOperationRecipientSummary;
  mail: BulkEmailOperationMailPreview;
};

export type PreviewBulkEmailOperationPayload = {
  source_type: BulkEmailOperationSourceType;
  template_id: string;
  smtp_account_id: string;
  subject_override: string | null;
  manual_emails?: string | null;
  fair_ids?: string[];
  country_filter?: string | null;
  city_filter?: string | null;
  company_name_contains?: string | null;
  recipient_options?: BulkEmailOperationRecipientOptions;
  excel_file?: File | null;
};

export type SendBulkEmailOperationPayload = {
  source_type: BulkEmailOperationSourceType;
  template_id: string;
  smtp_account_id: string;
  subject: string;
  title?: string | null;
  manual_emails?: string | null;
  fair_ids?: string[];
  country_filter?: string | null;
  city_filter?: string | null;
  company_name_contains?: string | null;
  recipient_options?: BulkEmailOperationRecipientOptions;
  client_token?: string | null;
  excel_file?: File | null;
};

export type BulkEmailOperationSendResponse = {
  operation_id: string;
  batch_id: string | null;
  status: string;
  total_count: number;
  message: string;
};

export type BulkEmailOperationRecipientRow = {
  id: string;
  email: string;
  company_name: string;
  recipient_name: string | null;
  source: string;
  fair_name: string | null;
  status: string;
  error_message: string | null;
  send_attempt: number;
  sent_at: string | null;
  customer_id: string | null;
  contact_id: string | null;
  participation_id: string | null;
};

export type BulkEmailOperationRecipientsResponse = {
  batch_id: string;
  items: BulkEmailOperationRecipientRow[];
};

export type BulkEmailOperationLogLine = {
  at: string | null;
  level: string;
  message: string;
  outbox_id: string | null;
  email: string | null;
  status: string | null;
};

export type BulkEmailOperationLogsResponse = {
  batch_id: string;
  items: BulkEmailOperationLogLine[];
};

export type BulkEmailOperationExportFormat = "json" | "excel";
