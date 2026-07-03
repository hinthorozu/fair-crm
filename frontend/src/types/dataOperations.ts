export type DuplicateGroupByField = "company_name" | "email" | "website" | "phone";

export interface DataOperationOutputFile {
  id: string;
  file_name: string;
  relative_path: string;
  size_bytes: number | null;
}

export interface DataOperationRun {
  id: string;
  operation_key: string;
  status: "queued" | "running" | "completed" | "failed";
  started_by: string;
  started_by_email: string | null;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  result: "success" | "failed" | null;
  error_message: string | null;
  output_files: DataOperationOutputFile[];
  summary_json: Record<string, string | number> | null;
  result_mode: "file" | "dataset" | null;
  dataset_kind: string | null;
}

export interface DataOperationDefinition {
  key: string;
  name: string;
  description: string;
  destructive: boolean;
  output_mode: "excel" | "directory" | "none" | "dataset";
  result_mode: "file" | "dataset";
  dataset_kind: string | null;
  last_run: DataOperationRun | null;
  active_run: DataOperationRun | null;
}

export interface DataOperationsListResponse {
  items: DataOperationDefinition[];
}

export interface RunDataOperationResponse {
  id: string;
  operation_key: string;
  status: string;
  result_mode: "file" | "dataset" | null;
  dataset_kind: string | null;
}

export interface RunDataOperationRequest {
  group_by?: DuplicateGroupByField;
}

export interface AssignCustomersToFairResponse {
  id: string;
  operation_key: string;
  status: string;
  parent_run_id: string;
  fair_id: string;
  selected_count: number;
}

export interface DeleteSelectedCustomersResponse {
  id: string;
  operation_key: string;
  status: string;
  parent_run_id: string;
  selected_count: number;
}

export interface AssignCustomersToFairSummary {
  assigned_count?: number;
  skipped_count?: number;
  failed_count?: number;
  fair_name?: string;
}

export interface DataOperationDatasetSummary {
  total_customers: number;
  customers_with_fair: number;
  customers_without_fair: number;
}

export interface DuplicateDatasetCustomer {
  id: string;
  display_name: string;
  legal_name: string | null;
  trade_name: string | null;
  customer_type: string;
  status: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
  group_key: string;
  group_by: string | null;
  fair_count: number;
  first_fair: string | null;
}

export interface DataOperationDuplicateDatasetSummary {
  group_by?: string;
  total_customers: number;
  duplicate_groups: number;
  customers_in_duplicate_groups: number;
}

export interface DuplicateDatasetGroup {
  group_key: string;
  group_by: string;
  customer_count: number;
  fair_count: number;
  fair_names: string[];
  suggested_winner_customer_id: string;
  suggested_winner_company_name: string;
  created_at_min: string;
  created_at_max: string;
}

export interface DuplicateGroupParticipation {
  fair_name: string;
  fair_year: number | null;
  hall: string | null;
  stand: string | null;
}

export interface DuplicateGroupCustomerPhone {
  id: string;
  phone: string;
  is_primary: boolean;
  created_at: string;
}

export interface DuplicateGroupCustomerEmail {
  id: string;
  email: string;
  is_primary: boolean;
  created_at: string;
}

export interface DuplicateGroupCustomerWebsite {
  id: string;
  website: string;
  is_primary: boolean;
  created_at: string;
}

export interface DuplicateGroupCustomerDetail {
  id: string;
  company_name: string;
  legal_name: string | null;
  trade_name: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  phones: DuplicateGroupCustomerPhone[];
  emails: DuplicateGroupCustomerEmail[];
  websites: DuplicateGroupCustomerWebsite[];
  city: string | null;
  country: string | null;
  status: string;
  created_at: string;
  participations: DuplicateGroupParticipation[];
}

export interface DuplicateDatasetGroupDetail {
  group_key: string;
  group_by: string;
  customers: DuplicateGroupCustomerDetail[];
  merge_policy: string;
}

export interface DuplicateGroupScalarSelectionsRequest {
  company_name: string;
  legal_name: string;
  trade_name: string;
  city: string;
  country: string;
}

export interface DuplicateGroupMergePreviewRequest {
  run_id: string;
  surviving_customer_id: string;
  scalar_selections: DuplicateGroupScalarSelectionsRequest;
  selected_email_ids: string[];
  selected_phone_ids: string[];
  selected_website_ids: string[];
}

export interface DuplicateGroupMergePreviewCommunication {
  value: string;
  is_primary: boolean;
  source_customer_id: string;
  source_customer_name: string;
  source_row_id: string;
}

export interface DuplicateGroupMergePreviewScalarFields {
  company_name: string;
  legal_name: string | null;
  trade_name: string | null;
  city: string | null;
  country: string | null;
}

export interface DuplicateGroupMergePreviewParticipationSummary {
  total_participation_rows: number;
  unique_fairs: number;
  fair_names: string[];
}

export interface DuplicateGroupMergePreviewStatistics {
  customers_before: number;
  customers_after: number;
  emails_before: number;
  emails_after: number;
  phones_before: number;
  phones_after: number;
  websites_before: number;
  websites_after: number;
}

export interface DuplicateGroupMergePreviewIssue {
  code: string;
  message: string;
  severity: "error" | "warning";
}

export interface DuplicateGroupMergePreviewMergedCustomer {
  id: string;
  display_name: string;
  legal_name: string | null;
  trade_name: string | null;
  normalized_name: string;
  customer_type: string;
  status: string;
  website: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
  phones: DuplicateGroupCustomerPhone[];
  emails: DuplicateGroupCustomerEmail[];
  websites: DuplicateGroupCustomerWebsite[];
}

export interface DuplicateGroupMergePreview {
  group_key: string;
  group_by: string;
  surviving_customer_id: string;
  merged_customer: DuplicateGroupMergePreviewMergedCustomer;
  scalar_fields: DuplicateGroupMergePreviewScalarFields;
  emails: DuplicateGroupMergePreviewCommunication[];
  phones: DuplicateGroupMergePreviewCommunication[];
  websites: DuplicateGroupMergePreviewCommunication[];
  participation_summary: DuplicateGroupMergePreviewParticipationSummary;
  customers_to_archive: string[];
  validation_errors: DuplicateGroupMergePreviewIssue[];
  warnings: DuplicateGroupMergePreviewIssue[];
  statistics: DuplicateGroupMergePreviewStatistics;
  is_valid: boolean;
}

export type DuplicateGroupMergeExecuteRequest = DuplicateGroupMergePreviewRequest;

export interface DuplicateGroupMergeExecuteResponse {
  group_key: string;
  group_by: string;
  surviving_customer: DuplicateGroupMergePreviewMergedCustomer;
  customers_deleted: string[];
  statistics: DuplicateGroupMergePreviewStatistics;
}
