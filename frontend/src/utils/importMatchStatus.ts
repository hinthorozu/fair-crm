import type { ImportRow } from "../types/import";

/** User-facing match/decision status for import analyze preview. */
export type ImportMatchStatus =
  | "new_customer"
  | "existing_customer_candidate"
  | "no_company_name"
  | "invalid_company_name"
  | "batch_duplicate";

export function getImportMatchStatus(row: ImportRow): ImportMatchStatus {
  const errors = row.validation_errors_json ?? [];
  if (errors.includes("no_company_name")) return "no_company_name";
  if (errors.includes("invalid_company_name")) return "invalid_company_name";
  if (errors.includes("batch_duplicate_company_name")) return "batch_duplicate";

  if (row.match_customer_id) return "existing_customer_candidate";
  if (row.status === "ready_to_create") return "new_customer";
  if (row.status === "invalid") return "invalid_company_name";
  return "new_customer";
}

export function formatMatchConfidence(confidence: number | null): string {
  if (confidence == null) return "—";
  return `${(confidence / 100).toFixed(2)}`;
}
