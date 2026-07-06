export type WorklistFilter = "yapilmadi" | "takipte" | "konu_kapandi" | "hepsi";

export type WorklistPrimaryStatus = "not_started" | "in_follow_up" | "closed";

export interface TodoWorklistRow {
  customer_id: string;
  customer_name: string;
  city: string | null;
  country: string | null;
  phone_summary: string | null;
  email_summary: string | null;
  contact_count: number;
  participation_id: string;
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

export interface TodoWorklistProgress {
  total: number;
  not_started: number;
  in_follow_up: number;
  closed: number;
}

export interface TodoWorklistOutcomeOption {
  id: string;
  name: string;
  code: string;
  primary_worklist_status: "in_follow_up" | "closed";
  requires_action: boolean;
  marks_data_problem: boolean;
}

export interface TodoWorklistModalActivity {
  id: string;
  subject: string;
  description: string | null;
  activity_date: string;
  follow_up_date: string | null;
}

export interface TodoWorklistModalContext {
  todo_id: string;
  todo_title: string;
  customer_id: string;
  customer_name: string;
  city: string | null;
  country: string | null;
  phone_summary: string | null;
  email_summary: string | null;
  contact_count: number;
  worklist_row: TodoWorklistRow | null;
  outcomes: TodoWorklistOutcomeOption[];
  recent_activities: TodoWorklistModalActivity[];
}

export interface RecordTodoWorklistActivityPayload {
  outcome_id: string;
  note: string;
  activity_type?: string;
  follow_up_at?: string | null;
  action_required?: boolean;
  data_problem?: boolean;
  advance_to_next?: boolean;
}

export interface RecordTodoWorklistActivityResult {
  activity_id: string;
  worklist_row: TodoWorklistRow;
  progress: TodoWorklistProgress;
  next_customer_id: string | null;
}
