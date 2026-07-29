export interface TodoStep {
  id: string;
  organization_id: string;
  todo_id: string;
  title: string;
  sort_order: number;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReplaceTodoStepsPayload {
  steps: Array<{ id?: string; title: string }>;
}

export interface UpdateTodoStepPayload {
  title?: string;
  is_completed?: boolean;
}
