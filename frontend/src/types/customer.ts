export type CustomerType =
  | "exhibitor"
  | "visitor"
  | "supplier"
  | "sponsor"
  | "organizer"
  | "partner"
  | "lead"
  | "other";

export type CustomerStatus = "lead" | "active" | "inactive" | "archived";

export type CustomerSource = "manual" | "excel" | "scraper";

export interface CustomerPhone {
  id: string;
  phone: string;
  is_primary: boolean;
  created_at: string;
}

export interface CustomerEmail {
  id: string;
  email: string;
  is_primary: boolean;
  created_at: string;
}

export interface CustomerWebsite {
  id: string;
  website: string;
  is_primary: boolean;
  created_at: string;
}

export interface CustomerPhoneInput {
  phone: string;
  is_primary: boolean;
}

export interface CustomerEmailInput {
  email: string;
  is_primary: boolean;
}

export interface CustomerWebsiteInput {
  website: string;
  is_primary: boolean;
}

export interface Customer {
  id: string;
  organization_id: string;
  display_name: string;
  legal_name: string | null;
  trade_name: string | null;
  normalized_name: string;
  customer_type: CustomerType;
  status: CustomerStatus;
  website: string | null;
  phone: string | null;
  email: string | null;
  tax_number: string | null;
  tax_office: string | null;
  country: string | null;
  city: string | null;
  district: string | null;
  address: string | null;
  description: string | null;
  instagram_url: string | null;
  facebook_url: string | null;
  linkedin_url: string | null;
  youtube_url: string | null;
  source: CustomerSource;
  email_allowed: boolean;
  sms_allowed: boolean;
  email_unsubscribed_at: string | null;
  sms_unsubscribed_at: string | null;
  consent_note: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  phones?: CustomerPhone[];
  emails?: CustomerEmail[];
  websites?: CustomerWebsite[];
  phone_extra_count?: number;
  email_extra_count?: number;
  website_extra_count?: number;
}

export interface CustomerListResponse {
  items: Customer[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CreateCustomerPayload {
  display_name: string;
  legal_name?: string | null;
  trade_name?: string | null;
  customer_type?: CustomerType;
  status?: CustomerStatus;
  phones?: CustomerPhoneInput[];
  emails?: CustomerEmailInput[];
  websites?: CustomerWebsiteInput[];
  /** @deprecated Use phones[] — kept for backward-compatible API clients */
  website?: string | null;
  /** @deprecated Use phones[] */
  phone?: string | null;
  /** @deprecated Use emails[] */
  email?: string | null;
  country?: string | null;
  city?: string | null;
  district?: string | null;
  address?: string | null;
  description?: string | null;
  instagram_url?: string | null;
  facebook_url?: string | null;
  linkedin_url?: string | null;
  youtube_url?: string | null;
  source?: CustomerSource;
  email_allowed?: boolean;
  sms_allowed?: boolean;
  consent_note?: string | null;
}

export type UpdateCustomerPayload = Partial<CreateCustomerPayload>;

export interface ListCustomersParams {
  search?: string;
  status?: CustomerStatus;
  customer_type?: CustomerType;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
