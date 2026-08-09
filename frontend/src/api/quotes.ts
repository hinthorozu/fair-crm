import { apiRequest } from "./client";
import type { Quote, QuotePayload } from "../types/quote";

export const getQuoteByTodo = (todoId: string) => apiRequest<Quote | null>(`/api/v1/quotes/todo/${encodeURIComponent(todoId)}`);
export const createQuoteByTodo = (todoId: string, payload: QuotePayload) => apiRequest<Quote>(`/api/v1/quotes/todo/${encodeURIComponent(todoId)}`, { method: "POST", body: JSON.stringify(payload) });
export const updateQuoteByTodo = (todoId: string, payload: QuotePayload) => apiRequest<Quote>(`/api/v1/quotes/todo/${encodeURIComponent(todoId)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const renderQuoteByTodo = (todoId: string) => apiRequest<{ html: string }>(`/api/v1/quotes/todo/${encodeURIComponent(todoId)}/render`);
