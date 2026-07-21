export type AdapterEngineType = "static" | "dynamic";

export type ScraperRunStatus =
  | "running"
  | "cancel_requested"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled";

export type ScraperRunLogLevel = "info" | "warning" | "error" | "success";

export interface AdapterFeature {
  key: string;
  label: string;
  enabled: boolean;
}

export interface AdapterListItem {
  id: string | null;
  adapter_key: string;
  engine_key: string;
  engine_type: AdapterEngineType;
  display_name: string;
  version: string;
  features: AdapterFeature[];
  last_verified: string | null;
  actions_available: string[];
  description?: string | null;
  is_active: boolean;
  is_registered: boolean;
}

export interface AdapterDetail {
  id: string | null;
  adapter_key: string;
  engine_key: string;
  engine_type: AdapterEngineType;
  name: string;
  description: string | null;
  version: string;
  manifest: Record<string, unknown> | null;
  is_active: boolean;
  is_registered: boolean;
  last_verified: string | null;
  last_verified_at: string | null;
  features: AdapterFeature[];
  actions_available: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface AdapterDeletePreviewActiveRun {
  id: string;
  fair_name: string | null;
  input_url: string | null;
  started_at: string;
}

export interface AdapterDeletePreview {
  adapter_key: string;
  display_name: string;
  linked_fairs_count: number;
  affected_fairs: string[];
  active_runs_count: number;
  active_runs: AdapterDeletePreviewActiveRun[];
}

export interface AdapterEngine {
  engine_key: string;
  display_name: string;
  engine_type: AdapterEngineType;
  version: string;
  supported_sites: string[];
  features: AdapterFeature[];
  actions_available: string[];
  is_runnable: boolean;
}

export interface AdapterEngineListResponse {
  items: AdapterEngine[];
  total: number;
}

export interface AdapterListResponse {
  items: AdapterListItem[];
  total: number;
}

export interface CreateAdapterPayload {
  name: string;
  description?: string | null;
  engine_key?: string | null;
  version?: string | null;
  last_verified?: string | null;
  supported_sites?: string[] | string;
  output?: { json_handoff?: boolean; excel?: boolean };
  browser?: { requires_js?: boolean; requires_playwright?: boolean };
  requested_fields?: RequestedOutputField[];
  is_active?: boolean;
}

export interface UpdateAdapterPayload {
  name?: string;
  description?: string | null;
  version?: string | null;
  manifest?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface UpdateAdapterManifestPayload {
  display_name?: string;
  version?: string;
  last_verified?: string | null;
  supported_sites?: string[] | string;
  notes?: string | null;
  output?: { json_handoff?: boolean; excel?: boolean };
  browser?: { requires_js?: boolean; requires_playwright?: boolean };
  supports?: Partial<ScraperSupports>;
  requested_fields?: RequestedOutputField[];
}

export type RequestedOutputField =
  | "customerName"
  | "phone"
  | "email"
  | "address"
  | "website"
  | "hall"
  | "stand"
  | "instagram"
  | "facebook"
  | "linkedin"
  | "youtube"
  | "notes";

export interface ScraperDashboardSummary {
  total_adapters: number;
  last_run_adapter: string | null;
  failed_scraper_count: number;
}

export interface ScraperDashboardResponse {
  summary: ScraperDashboardSummary;
  adapters: AdapterListItem[];
}

export interface ScraperManifestListResponse {
  items: AdapterListItem[];
  total: number;
}

export interface ScraperSupports {
  list_scraping: boolean;
  detail_scraping: boolean;
  pagination: boolean;
  website: boolean;
  email: boolean;
  phone: boolean;
  address: boolean;
  category: boolean;
  description: boolean;
}

export interface ScraperManifest {
  adapter_key: string;
  display_name: string;
  version: string;
  supported_sites: string[];
  supports: ScraperSupports;
  output: { json_handoff: boolean; excel: boolean };
  browser: { requires_js: boolean; requires_playwright: boolean };
  author: string;
  notes: string;
  scraper_version: string;
  target_site_version: string;
  last_verified: string | null;
  requested_fields?: RequestedOutputField[];
}

export interface ScraperRun {
  id: string;
  adapter_key: string;
  status: ScraperRunStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  organization_id: string | null;
  fair_id: string | null;
  input_url: string | null;
  fair_name: string | null;
  fair_year: number | null;
  total_rows: number;
  website_count: number;
  email_count: number;
  phone_count: number;
  instagram_count: number;
  linkedin_count: number;
  facebook_count: number;
  youtube_count: number;
  x_count: number;
  error_message: string | null;
  output_json_path: string | null;
  output_excel_path: string | null;
  adapter_name?: string | null;
  engine_key?: string | null;
  engine_type?: AdapterEngineType | null;
  output_json_available?: boolean;
  output_excel_available?: boolean;
  json_download_url?: string | null;
  json_view_url?: string | null;
  excel_download_url?: string | null;
  excel_view_url?: string | null;
  run_source?: "fair_automation" | "manual_test" | "enrichment";
  import_batch_id?: string | null;
  import_batch_url?: string | null;
  enrichment_summary?: EnrichmentRunSummary | null;
  cancel_requested_by?: string | null;
  cancel_requested_at?: string | null;
  last_heartbeat_at?: string | null;
  progress_current?: number | null;
  progress_total?: number | null;
}

export interface ScraperRunCancelResponse {
  job_id: string;
  status: ScraperRunStatus;
  cancel_requested_at: string | null;
  message: string;
}

export interface EnrichmentRunSummary {
  customers_scanned: number;
  emails_found: number;
  phones_found?: number;
  not_found: number;
  failed: number;
  found: number;
  import_rows: number;
  dry_run: boolean;
  import_batch_created: boolean;
  import_batch_id: string | null;
}

export type CompanyNameMatchMode = "contains" | "starts_with";

export interface EnrichmentRunPayload {
  /** Omitted/undefined falls back to the backend default; explicit `null` means "no limit — all eligible customers". */
  limit?: number | null;
  requested_fields?: RequestedOutputField[];
  max_pages?: number;
  /** When true, customers who already have a CRM email are also scanned for new data. */
  include_existing_email?: boolean;
  /** Optional fair scope — only participants of this fair are candidates. */
  fair_id?: string | null;
  /** Optional company-name filter (contains / starts_with). */
  company_name?: string | null;
  company_name_match?: CompanyNameMatchMode;
  /** Optional address/city substring filter. */
  address_contains?: string | null;
}

export interface EnrichmentStateResetPayload {
  customer_ids?: string[];
  reset_all?: boolean;
}

export interface EnrichmentStateResetResponse {
  deleted_count: number;
}

export interface ScraperRunListResponse {
  items: ScraperRun[];
  total: number;
}

export interface ScraperRunLog {
  id: string;
  run_id: string;
  level: ScraperRunLogLevel;
  step: string;
  message: string;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface ScraperRunLogListResponse {
  items: ScraperRunLog[];
  total: number;
  run_status: ScraperRunStatus;
  total_rows: number;
  output_json_available: boolean;
  output_excel_available: boolean;
}

export interface AdapterLinkedFair {
  id: string | null;
  name: string;
  venue: string | null;
  city: string | null;
  status: string | null;
  source_url: string | null;
  last_import_at: string | null;
}

export interface AdapterLinkedFairListResponse {
  items: AdapterLinkedFair[];
  total: number;
}
