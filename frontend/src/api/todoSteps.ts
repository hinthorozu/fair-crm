import { apiRequest } from "./client";
import type { ReplaceTodoStepsPayload, TodoStep, UpdateTodoStepPayload } from "../types/todoStep";

export function listTodoSteps(todoId: string): Promise<TodoStep[]> {
  return apiRequest<TodoStep[]>(`/api/v1/todos/${todoId}/steps`);
}

export function replaceTodoSteps(
  todoId: string,
  payload: ReplaceTodoStepsPayload,
): Promise<TodoStep[]> {
  return apiRequest<TodoStep[]>(`/api/v1/todos/${todoId}/steps`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateTodoStep(
  todoId: string,
  stepId: string,
  payload: UpdateTodoStepPayload,
): Promise<TodoStep> {
  return apiRequest<TodoStep>(`/api/v1/todos/${todoId}/steps/${stepId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTodoStep(todoId: string, stepId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/todos/${todoId}/steps/${stepId}`, {
    method: "DELETE",
  });
}
