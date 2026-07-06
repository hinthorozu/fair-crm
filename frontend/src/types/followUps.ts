import type { WorklistPrimaryStatus } from "./todoWorklist";

export type FollowUpFilter = "bugun" | "gecmis" | "action_required" | "data_problem" | "hepsi";

export interface FollowUpRow {
  todo_id: string;
  todo_title: string;
  customer_id: string;
  customer_name: string;
  city: string | null;
  country: string | null;
  phone_summary: string | null;
  email_summary: string | null;
  contact_count: number;
  participation_id: string | null;
  primary_status: WorklistPrimaryStatus;
  last_outcome_id: string | null;
  last_outcome_name: string | null;
  last_note_summary: string | null;
  last_activity_at: string | null;
  follow_up_at: string | null;
  action_required: boolean;
  data_problem: boolean;
  added_after_completion: boolean;
}
