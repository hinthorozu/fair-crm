export interface QuoteTemplate {
  id: string;
  organization_id: string;
  name: string;
  current_version_id: string;
  version_number: number;
  logo_url: string | null;
  source_code: string;
  created_at: string;
  updated_at: string;
}

export interface QuoteTemplatePayload {
  name: string;
  logo_url: string | null;
  source_code: string;
}
