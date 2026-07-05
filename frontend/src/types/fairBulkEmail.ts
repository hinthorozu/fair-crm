/** Fair bulk email types */

export interface RecipientOptions {
  include_customer_emails: boolean;
  include_contact_emails: boolean;
  skip_no_email: boolean;
  exclude_inactive: boolean;
  dedupe_emails: boolean;
}

export const DEFAULT_RECIPIENT_OPTIONS: RecipientOptions = {
  include_customer_emails: true,
  include_contact_emails: true,
  skip_no_email: true,
  exclude_inactive: true,
  dedupe_emails: true,
};

export interface RecipientPreviewItem {
  recipient_key: string;
  recipient_name: string | null;
  company_name: string;
  email: string;
  source: "customer" | "contact";
  customer_id: string;
  contact_id: string | null;
  participation_id: string;
  status: "will_send" | "skip";
  skip_reason: string | null;
}

export interface RecipientPreviewSummary {
  total_customers: number;
  total_contacts: number;
  valid_email_count: number;
  deduped_recipient_count: number;
  skipped_count: number;
  recipients: RecipientPreviewItem[];
}

export interface BulkEmailContentPreview {
  subject: string;
  body_html: string | null;
  body_text: string | null;
  sample_recipient: RecipientPreviewItem;
  total_send_count: number;
}

export interface SendBulkEmailResponse {
  batch_id: string;
  status: string;
  total_count: number;
  skipped_count: number;
  message: string;
}

export interface PreviewBulkEmailPayload {
  template_id: string;
  sample_recipient_key?: string | null;
  subject_override?: string | null;
  recipient_options: RecipientOptions;
}

export interface SendBulkEmailPayload {
  template_id: string;
  smtp_account_id?: string | null;
  subject_override?: string | null;
  recipient_options: RecipientOptions;
}

export interface FairEmailBatchListItem {
  id: string;
  status: string;
  template_id: string;
  template_name: string | null;
  smtp_account_id: string | null;
  smtp_account_name: string | null;
  subject: string | null;
  total_recipients: number;
  queued_count: number;
  sent_count: number;
  failed_count: number;
  skipped_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface FairEmailBatchListResponse {
  items: FairEmailBatchListItem[];
}

export interface FairEmailBatchDetail {
  id: string;
  fair_id: string;
  status: string;
  template_id: string;
  template_name: string | null;
  smtp_account_id: string | null;
  smtp_account_name: string | null;
  subject: string | null;
  subject_override: string | null;
  total_recipients: number;
  queued_count: number;
  sent_count: number;
  failed_count: number;
  skipped_count: number;
  created_at: string;
  completed_at: string | null;
  created_by_user_id: string;
}

export interface FairEmailOutboxItem {
  id: string;
  recipient_email: string;
  recipient_name: string | null;
  company_name: string;
  recipient_source: string;
  customer_id: string;
  contact_id: string | null;
  status: string;
  error_message: string | null;
  attempts: number;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FairEmailBatchDetailResponse {
  batch: FairEmailBatchDetail;
  items: FairEmailOutboxItem[];
}
