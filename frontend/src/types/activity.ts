export type ActivityType =
  | "call"
  | "meeting"
  | "email"
  | "whatsapp"
  | "note"
  | "fair_visit"
  | "follow_up"
  | "other";

export type ActivityStatus = "open" | "completed" | "cancelled";

export type ActivitySource =
  | "manual"
  | "system"
  | "email_automation"
  | "whatsapp_integration"
  | "import"
  | "other";

export interface Activity {
  id: string;
  organization_id: string;
  customer_id: string;
  contact_id: string | null;
  contact_full_name: string | null;
  type: ActivityType;
  subject: string;
  description: string | null;
  activity_date: string;
  follow_up_date: string | null;
  status: ActivityStatus;
  source: ActivitySource;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ActivityListResponse {
  items: Activity[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CreateActivityPayload {
  customer_id: string;
  type: ActivityType;
  subject: string;
  activity_date: string;
  status: ActivityStatus;
  contact_id?: string | null;
  description?: string | null;
  follow_up_date?: string | null;
  source?: ActivitySource;
  is_active?: boolean;
}

export interface UpdateActivityPayload {
  type?: ActivityType;
  subject?: string;
  activity_date?: string;
  status?: ActivityStatus;
  contact_id?: string | null;
  description?: string | null;
  follow_up_date?: string | null;
  source?: ActivitySource;
  is_active?: boolean;
}

export interface ListActivitiesParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
