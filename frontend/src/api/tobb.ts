import { apiRequest } from "./client";
import { coreRequest } from "./organizations";

const base = "/api/v1/fairs/system/tobb";
export interface TobbReview {
  id: string; fair_id: string | null; kind: string; name: string; status: string; version: number;
  stored_values: Record<string, unknown>; proposed_values: Record<string, unknown>;
  source_row: Record<string, unknown>;
}
export interface TobbChange {
  action: string; name: string; kind?: string;
  stored_values?: Record<string, unknown>; proposed_values?: Record<string, unknown>;
  source?: Record<string, unknown>;
}
export interface TobbYearResult {
  status: string; attempts: number; inserted?: number; updated?: number; skipped?: number; reviews?: number;
  error?: string; changes?: TobbChange[]; details?: TobbChange[];
}
export interface TobbRun {
  id: string; status: string; run_source: string; requested_by: string | null;
  started_at: string; finished_at: string | null; duration_ms: number | null;
  progress_current: number; progress_total: number; error_message: string | null;
  summary: {phase: string; years: number[]; year_results: Record<string, TobbYearResult>; notification?: string; notification_error?: string; requested_by_label?: string};
}
export interface TobbDecision { id: string; version: number; decision: string; target_fair_id?: string; source_external_id?: string }
export const getTobbRun = (id: string) => apiRequest<TobbRun>(`${base}/runs/${encodeURIComponent(id)}`);
export const listTobbRuns = (offset = 0) => apiRequest<{items: TobbRun[]}>(`${base}/runs?offset=${offset}`);
export const startTobbPreview = (year: number) => apiRequest<{run: TobbRun; started: boolean}>(`${base}/sync`, {method: "POST", body: JSON.stringify({year})});
export const applyTobbPreview = (id: string) => apiRequest<{run: TobbRun; started: boolean}>(`${base}/runs/${encodeURIComponent(id)}/apply`, {method: "POST"});
export const cancelTobbRun = (id: string) => apiRequest<TobbRun>(`${base}/runs/${encodeURIComponent(id)}/cancel`, {method: "POST"});
export const retryTobbRun = (id: string) => apiRequest<{run: TobbRun; started: boolean}>(`${base}/runs/${encodeURIComponent(id)}/retry`, {method: "POST"});
export const retryTobbNotification = (id: string) => apiRequest<TobbRun>(`${base}/runs/${encodeURIComponent(id)}/retry-notification`, {method: "POST"});
export const listTobbReviews = () => apiRequest<{items: TobbReview[]; counts: Record<string, number>; pending_count: number}>(`${base}/reviews`);
export const decideTobbReview = (body: TobbDecision) => apiRequest<TobbReview>(`${base}/reviews/decide`, {method: "POST", body: JSON.stringify(body)});
export const bulkTobbDates = (items: TobbDecision[]) => apiRequest<{items: {id: string; success: boolean; error?: string}[]}>(`${base}/reviews/dates/bulk`, {method: "POST", body: JSON.stringify({items})});
export const listSystemInAppNotifications = () => coreRequest<{id: string; subject: string; body: string; variables: {run_id?: string; path?: string} | null}[]>("/system/notifications/in-app");
export interface TobbMapping {id: string; identity_name: string; city: string; fair_id: string; name: string}
export const listTobbMappings = () => apiRequest<{items: TobbMapping[]}>(`${base}/mappings`);
export const changeTobbMapping = (id: string, fair_id: string) => apiRequest(`${base}/mappings/${encodeURIComponent(id)}`, {method: "PATCH", body: JSON.stringify({fair_id})});
