import type { StandardListResponse } from "./listTable";

export type ImportSourceType =
  | "excel"
  | "csv"
  | "api"
  | "pdf"
  | "scraper"
  | "database"
  | "manual"
  | "other";

export type ImportBatchStatus =
  | "uploaded"
  | "sheet_selected"
  | "header_configured"
  | "mapping_completed"
  | "analysis_queued"
  | "analyzing"
  | "analyzed"
  | "analysis_failed"
  | "decision_required"
  | "applying"
  | "completed"
  | "failed"
  | "cancelled"
  | "mapped"
  | "previewed"
  | "applied";

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

export interface ImportRowFilterCounts {
  pending: number;
  all: number;
  applied: number;
  new: number;
  will_update: number;
  duplicate: number;
  invalid: number;
  skip: number;
}

export interface ImportRowListResponse extends StandardListResponse<ImportRow> {
  counts?: ImportRowFilterCounts;
}

export type PreviewFilter =
  | "all"
  | "pending"
  | "applied"
  | "new"
  | "will_update"
  | "duplicate"
  | "invalid"
  | "skip";

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
  selected_sheet_name?: string | null;
  available_sheets?: string[];
  header_mode?: ExcelHeaderMode | null;
  has_header_row?: boolean | null;
  header_row_index?: number | null;
  column_mapping_json?: Record<string, { type: string; value: number }> | null;
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
  grid?: {
    columns: { index: number; letter: string; header: string | null }[];
    rows: unknown[][];
    total_data_rows: number;
    preview_row_count: number;
  };
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

export { WIZARD_MAPPING_FIELDS } from "../utils/outputFieldDefinitions";
