export type AdapterStatus = "stable" | "experimental" | "deprecated";

export type ScraperRunStatus = "running" | "completed" | "failed";

export type ScraperRunLogLevel = "info" | "warning" | "error" | "success";

export interface AdapterFeature {
  key: string;
  label: string;
  enabled: boolean;
}

export interface AdapterListItem {
  id: string | null;
  adapter_key: string;
  display_name: string;
  status: AdapterStatus | string;
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
  name: string;
  description: string | null;
  status: AdapterStatus | string;
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

export interface AdapterListResponse {
  items: AdapterListItem[];
  total: number;
}

export interface CreateAdapterPayload {
  adapter_key: string;
  name: string;
  description?: string | null;
  status?: AdapterStatus;
  version?: string | null;
  manifest?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface UpdateAdapterPayload {
  name?: string;
  description?: string | null;
  status?: AdapterStatus;
  version?: string | null;
  manifest?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface ScraperDashboardSummary {
  total_adapters: number;
  stable_count: number;
  experimental_count: number;
  deprecated_count: number;
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
  status: string;
  author: string;
  notes: string;
  scraper_version: string;
  target_site_version: string;
  last_verified: string | null;
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
