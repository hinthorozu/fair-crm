export type OperationType =
  | "scraper"
  | "email"
  | "bulk_email"
  | "enrichment"
  | "duplicate_check"
  | "data_cleanup"
  | "whatsapp"
  | "manual_task"
  | "reminder";

/** DB-backed operation type catalog row (display + capability metadata). */
export interface OperationTypeCatalogItem {
  key: string;
  name: string;
  is_active: boolean;
  sort_order: number;
  supports_pause: boolean;
  supports_resume: boolean;
  supports_retry: boolean;
  supports_schedule: boolean;
  supports_items: boolean;
  updated_at: string;
}

export type OperationTypeCapabilityKey =
  | "supports_pause"
  | "supports_resume"
  | "supports_retry"
  | "supports_schedule"
  | "supports_items";

export type UpdateOperationTypeCapabilitiesPayload = Record<
  OperationTypeCapabilityKey,
  boolean
> & {
  is_active: boolean;
};

export interface OperationTypeCatalogListResponse {
  items: OperationTypeCatalogItem[];
}

export type OperationStatus =
  | "draft"
  | "ready"
  | "active"
  | "completed"
  | "cancelled"
  | "archived";

export type SourceKind =
  | "fair"
  | "import"
  | "segment"
  | "manual_selection"
  | "customer"
  | "none";

export type OperationPriority = "low" | "normal" | "high" | "urgent";

export type RunStatus =
  | "queued"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export interface HandlerCapabilities {
  supports_pause: boolean;
  supports_resume: boolean;
  supports_retry: boolean;
  supports_schedule: boolean;
  supports_items: boolean;
}

export interface OperationRun {
  id: string;
  organization_id: string;
  operation_id: string;
  status: RunStatus | string;
  progress: number;
  total_items: number;
  processed_items: number;
  succeeded_items: number;
  failed_items: number;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  error_message: string | null;
  error_details: Record<string, unknown>;
  core_job_id: string | null;
  triggered_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface Operation {
  id: string;
  organization_id: string;
  operation_type: OperationType | string;
  title: string;
  description: string | null;
  status: OperationStatus | string;
  source_kind: SourceKind | string;
  source_ids: string[];
  source_config: Record<string, unknown>;
  type_config: Record<string, unknown>;
  run_settings: Record<string, unknown>;
  priority: OperationPriority | string;
  latest_run_id: string | null;
  related_todo_id?: string | null;
  related_resource?: { type: string; id: string } | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  capabilities: Partial<HandlerCapabilities>;
  latest_run?: OperationRun | null;
}

export interface OperationDetail {
  operation: Operation;
  runs: OperationRun[];
}

export interface WizardStepMeta {
  id: string;
  required: boolean;
  order: number;
}

export interface OperationTypeMetadata {
  type: OperationType | string;
  label_key: string;
  description_key: string;
  supported_sources: SourceKind[];
  default_source: SourceKind | string;
  capabilities: HandlerCapabilities;
  wizard_steps: WizardStepMeta[];
  type_config_schema: Record<string, unknown>;
  run_settings_schema: Record<string, unknown>;
  available_in_wizard: boolean;
  handler_registered: boolean;
}

export interface WizardMetadata {
  types: OperationTypeMetadata[];
  source_kinds: SourceKind[];
  capabilities_keys: string[];
}

export interface CreateOperationPayload {
  operation_type: OperationType;
  title: string;
  description?: string | null;
  source_kind?: SourceKind;
  source_ids?: string[];
  source_config?: Record<string, unknown>;
  type_config?: Record<string, unknown>;
  run_settings?: Record<string, unknown>;
  priority?: OperationPriority;
  status?: OperationStatus;
  start_immediately?: boolean;
}
