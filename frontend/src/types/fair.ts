export type FairStatus = "planned" | "active" | "completed" | "cancelled" | "archived";

export interface Fair {
  id: string;
  organization_id: string | null;
  origin: "organization" | "system";
  name: string;
  organizer: string | null;
  venue: string | null;
  city: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  website: string | null;
  status: FairStatus;
  description: string | null;
  adapter_key: string | null;
  source_url: string | null;
  scraper_config: Record<string, unknown> | null;
  normalized_name: string;
  scraped_record_count: number | null;
  scraped_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export function systemFairScrapeReady(
  fair: Pick<Fair, "scraped_record_count" | "scraped_at">,
): boolean {
  return fair.scraped_record_count != null && fair.scraped_at != null;
}

export interface FairListResponse {
  items: Fair[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CreateFairPayload {
  name: string;
  organizer?: string | null;
  venue?: string | null;
  city?: string | null;
  country?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  website?: string | null;
  status?: FairStatus;
  description?: string | null;
  adapter_key?: string | null;
  source_url?: string | null;
  scraper_config?: Record<string, unknown> | null;
}

export type UpdateFairPayload = Partial<CreateFairPayload>;

export interface ListFairsParams {
  search?: string;
  status?: FairStatus;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
