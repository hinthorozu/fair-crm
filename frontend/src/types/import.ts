export type ImportSourceType =
  | "excel"
  | "pdf"
  | "scraper"
  | "database"
  | "manual"
  | "other";

export type ImportBatchStatus =
  | "uploaded"
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

export type ImportDecision = "create_new" | "update_existing" | "skip";

export interface ImportBatch {
  id: string;
  organization_id: string;
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
  decision: ImportDecision | null;
  created_customer_id: string | null;
  updated_customer_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportRowListResponse {
  items: ImportRow[];
  total: number;
}

export interface ApplyImportResponse {
  batch: ImportBatch;
  created_rows: number;
  updated_rows: number;
  skipped_rows: number;
  invalid_rows: number;
}

export interface SetImportRowDecisionPayload {
  decision: ImportDecision;
  match_customer_id?: string;
}
