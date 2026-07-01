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
  source: CustomerSource;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
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
  website?: string | null;
  phone?: string | null;
  email?: string | null;
  country?: string | null;
  city?: string | null;
  district?: string | null;
  address?: string | null;
  description?: string | null;
  source?: CustomerSource;
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
