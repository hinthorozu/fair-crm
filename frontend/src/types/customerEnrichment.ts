import type { ScraperRunLog } from "./scraper";

export interface CustomerContactEnrichmentState {
  customer_id: string;
  status: string;
  last_email_scan_at: string | null;
  last_email_found: string | null;
  last_source_url: string | null;
  last_error: string | null;
  retry_after: string | null;
  last_enrichment_run_id: string | null;
  import_batch_id: string | null;
  can_run: boolean;
  block_code: string | null;
  block_message: string | null;
  website: string | null;
  has_crm_email: boolean;
  recent_logs: ScraperRunLog[];
}

export interface CustomerContactEnrichmentRunPayload {
  dry_run?: boolean;
  requested_fields?: string[];
  max_pages?: number;
}
