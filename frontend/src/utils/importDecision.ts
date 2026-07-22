import type { ImportDecision, ImportRow } from "../types/import";

/** Row decision persisted on the server, or analyze-derived default when unset. */
export function getEffectiveImportDecision(row: ImportRow): ImportDecision | "" {
  if (row.decision) {
    return row.decision;
  }
  if (row.status === "invalid") {
    return "skip";
  }
  if (row.match_customer_id) {
    return "update_existing";
  }
  if (row.status === "ready_to_create") {
    return "create_new";
  }
  if (row.status === "ready_to_update" || row.status === "possible_duplicate") {
    return "update_existing";
  }
  return "";
}

/** True while apply / bulk-assign / wizard loading should lock decision-list editing. */
export function isImportDecisionBusy(
  applyRunning: boolean,
  bulkAssignRunning: boolean,
  loading: boolean,
): boolean {
  return applyRunning || bulkAssignRunning || loading;
}
