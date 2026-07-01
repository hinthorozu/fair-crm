export type ParticipationStatus =
  | "planned"
  | "exhibitor"
  | "visited"
  | "contacted"
  | "follow_up_required"
  | "not_interested"
  | "customer"
  | "other";

export interface Participation {
  id: string;
  organization_id: string;
  customer_id: string;
  fair_id: string;
  hall: string | null;
  stand: string | null;
  participation_status: ParticipationStatus;
  notes: string | null;
  primary_contact_id: string | null;
  primary_contact_name: string | null;
  visited_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface CustomerParticipationListItem {
  id: string;
  fair_id: string;
  fair_name: string;
  fair_start_date: string | null;
  fair_end_date: string | null;
  hall: string | null;
  stand: string | null;
  participation_status: ParticipationStatus;
  primary_contact_name: string | null;
  visited_at: string | null;
  notes: string | null;
}

export interface FairParticipantListItem {
  id: string;
  customer_id: string;
  company_name: string;
  email: string | null;
  phone: string | null;
  country: string | null;
  city: string | null;
  hall: string | null;
  stand: string | null;
  participation_status: ParticipationStatus;
  primary_contact_name: string | null;
  visited_at: string | null;
  notes: string | null;
}

export interface CreateParticipationPayload {
  customer_id: string;
  fair_id: string;
  hall?: string | null;
  stand?: string | null;
  participation_status?: ParticipationStatus;
  notes?: string | null;
  primary_contact_id?: string | null;
  visited_at?: string | null;
}

export interface UpdateParticipationPayload {
  hall?: string | null;
  stand?: string | null;
  participation_status?: ParticipationStatus;
  notes?: string | null;
  primary_contact_id?: string | null;
  visited_at?: string | null;
  is_active?: boolean;
}

export interface CustomerParticipationListResponse {
  items: CustomerParticipationListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface FairParticipantListResponse {
  items: FairParticipantListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ListParticipationsParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
