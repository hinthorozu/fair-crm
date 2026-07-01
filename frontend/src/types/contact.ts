export interface Contact {
  id: string;
  organization_id: string;
  customer_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  title: string | null;
  department: string | null;
  email: string | null;
  phone: string | null;
  mobile_phone: string | null;
  linkedin: string | null;
  notes: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ContactListResponse {
  items: Contact[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CreateContactPayload {
  customer_id: string;
  first_name: string;
  last_name: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile_phone?: string;
  linkedin?: string;
  notes?: string;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface UpdateContactPayload {
  first_name?: string;
  last_name?: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
  mobile_phone?: string;
  linkedin?: string;
  notes?: string;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface ListContactsParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
