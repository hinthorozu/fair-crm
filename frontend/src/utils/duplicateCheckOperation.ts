import type { Operation } from "../types/operation";

/** Linked data-operation run payload stored on OperationRun.error_details.result. */
export function extractDuplicateCheckResultNav(
  operation: Operation,
): { runId: string; operationKey: string } | null {
  if (operation.operation_type !== "duplicate_check") return null;

  const rawResult = operation.latest_run?.error_details?.result;
  const result =
    rawResult && typeof rawResult === "object" && !Array.isArray(rawResult)
      ? (rawResult as Record<string, unknown>)
      : null;

  const runIdRaw = result?.data_operation_run_id;
  const runId = runIdRaw != null ? String(runIdRaw).trim() : "";
  if (!runId) return null;

  const keyFromResult = result?.operation_key != null ? String(result.operation_key).trim() : "";
  const keyFromConfig =
    operation.type_config?.job_key != null ? String(operation.type_config.job_key).trim() : "";
  const operationKey = keyFromResult || keyFromConfig;
  if (!operationKey) return null;

  return { runId, operationKey };
}
