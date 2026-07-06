export type TodoStatus = "todo" | "in_progress" | "done" | "cancelled" | "archived";

/** Status values allowed in create/edit forms (not done/archived). */
export type TodoFormStatus = "todo" | "in_progress" | "cancelled";

export type TodoPriority = "low" | "normal" | "high" | "urgent";

export type TodoCategory =
  | "arama"
  | "toplu_mail"
  | "sms"
  | "whatsapp"
  | "ziyaret"
  | "teklif"
  | "veri_temizleme"
  | "import_kontrol"
  | "musteri_guncelleme"
  | "genel_gorev"
  | "stand_tasarim"
  | "diger";

export interface Todo {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  status: TodoStatus;
  priority: TodoPriority;
  category: TodoCategory;
  deadline: string | null;
  assignee_user_id: string | null;
  source_fair_id: string | null;
  created_by: string;
  updated_by: string | null;
  archived_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface CreateTodoPayload {
  title: string;
  description?: string | null;
  status?: TodoFormStatus;
  priority?: TodoPriority;
  category?: TodoCategory;
  deadline?: string | null;
  assignee_user_id?: string | null;
  source_fair_id?: string | null;
}

export interface UpdateTodoPayload {
  title?: string;
  description?: string | null;
  status?: TodoFormStatus;
  priority?: TodoPriority;
  category?: TodoCategory;
  deadline?: string | null;
  assignee_user_id?: string | null;
  source_fair_id?: string | null;
}
