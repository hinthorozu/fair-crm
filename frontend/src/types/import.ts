export type ImportSourceType =
  | "excel"
  | "pdf"
  | "scraper"
  | "database"
  | "manual"
  | "other";

export type ImportBatchStatus =
  | "uploaded"
  | "mapped"
  | "analyzed"
  | "previewed"
  | "applied"
  | "failed"
  | "cancelled";

export type ImportRowStatus =
  | "pending"
  | "valid"
  | "invalid"
  | "possible_duplicate"
  | "ready_to_create"
  | "ready_to_update"
  | "applied"
  | "skipped";

export type MergeOutcome =
  | "same"
  | "new"
  | "will_add"
  | "will_update"
  | "will_keep"
  | "conflict"
  | "empty"
  | "skipped";

export interface MergeFieldPreview {
  field_key: string;
  label: string;
  crm_value: string | null;
  import_value: string | null;
  result_value: string | null;
  outcome: MergeOutcome;
  outcome_label: string;
}

export interface MergeEntityGroup {
  entity: string;
  entity_label: string;
  fields: MergeFieldPreview[];
}

export interface MergePreview {
  groups: MergeEntityGroup[];
  summary_lines: string[];
}

export type PreviewFilter = "all" | "new" | "will_update" | "duplicate" | "invalid" | "skip";

export type PreviewSortBy = "confidence" | "company_name" | "status";

export type ImportDecision =
  | "create_new"
  | "update_existing"
  | "participation_only"
  | "skip"
  | "manual_review";

export type ExcelHeaderMode = "first_row_header" | "no_header" | "manual_header_row";

export type BulkDecisionAction =
  | "create_all_new"
  | "link_all_existing"
  | "update_all_duplicates"
  | "skip_invalid";

export interface ImportBatch {
  id: string;
  organization_id: string;
  fair_id: string | null;
  source_type: ImportSourceType;
  file_name: string;
  status: ImportBatchStatus;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  created_rows: number;
  updated_rows: number;
  skipped_rows: number;
  created_participations: number;
  updated_participations: number;
  ready_to_create: number;
  ready_to_update: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  notes: string | null;
}

export interface ImportRow {
  id: string;
  batch_id: string;
  row_number: number;
  raw_data_json: Record<string, unknown>;
  normalized_data_json: Record<string, unknown>;
  status: ImportRowStatus;
  validation_errors_json: string[] | null;
  match_customer_id: string | null;
  match_customer_name: string | null;
  match_confidence: number | null;
  match_reason: string | null;
  participation_exists: boolean | null;
  suggested_action: string | null;
  decision: ImportDecision | null;
  created_customer_id: string | null;
  updated_customer_id: string | null;
  created_participation_id: string | null;
  updated_participation_id: string | null;
  merge_preview: MergePreview | null;
  created_at: string;
  updated_at: string;
}

export interface ImportRowListResponse {
  items: ImportRow[];
  total: number;
}

export interface UploadRawImportResponse {
  batch_id: string;
  fair_id: string;
  source_type: ImportSourceType;
  file_name: string;
  status: ImportBatchStatus;
  detected_headers: (string | null)[];
  raw_columns: { index: number; letter: string; sample_values: unknown[] }[];
  sample_rows: unknown[][];
  total_rows: number;
  suggested_mapping: {
    header_mode?: ExcelHeaderMode;
    has_header_row: boolean;
    header_row_index?: number | null;
    mappings: Record<string, { type: string; value: number }>;
  };
  available_sheets?: string[];
  selected_sheet_name?: string | null;
  mapping_columns?: MappingColumnPreview[];
}

export interface MappingColumnStats {
  total: number;
  empty: number;
  filled: number;
  first_value: string | null;
}

export interface MappingColumnPreview {
  key: string;
  index: number;
  letter: string;
  header: string | null;
  samples: (unknown | null)[];
  stats: MappingColumnStats;
}

export interface MappingPreviewResponse {
  batch_id: string;
  header_mode: ExcelHeaderMode;
  header_row_index: number | null;
  columns: MappingColumnPreview[];
}

export interface ColumnMappingPayload {
  has_header_row: boolean;
  header_mode?: ExcelHeaderMode;
  header_row_index?: number | null;
  mappings: Record<string, { type: "column_index"; value: number }>;
}

export interface ApplyImportResponse {
  batch: ImportBatch;
  created_rows: number;
  updated_rows: number;
  skipped_rows: number;
  invalid_rows: number;
  created_participations: number;
  updated_participations: number;
  created_contacts: number;
}

export interface SetImportRowDecisionPayload {
  decision: ImportDecision;
  match_customer_id?: string;
}

export const WIZARD_MAPPING_FIELDS: { key: string; label: string; required?: boolean }[] = [
  { key: "company_name", label: "Firma Adı", required: true },
  { key: "email", label: "E-posta" },
  { key: "phone", label: "Telefon" },
  { key: "mobile_phone", label: "Cep Telefonu" },
  { key: "website", label: "Web Sitesi" },
  { key: "country", label: "Ülke" },
  { key: "city", label: "Şehir" },
  { key: "address", label: "Adres" },
  { key: "tax_number", label: "Vergi No" },
  { key: "contact_first_name", label: "Yetkili Adı" },
  { key: "contact_last_name", label: "Yetkili Soyadı" },
  { key: "contact_title", label: "Yetkili Ünvanı" },
  { key: "contact_department", label: "Departman" },
  { key: "contact_email", label: "Yetkili E-posta" },
  { key: "contact_phone", label: "Yetkili Telefon" },
  { key: "contact_mobile_phone", label: "Yetkili Cep" },
  { key: "notes", label: "Notlar" },
  { key: "hall", label: "Salon" },
  { key: "stand", label: "Stand" },
];
