import type { OperationRun } from "../types/operation";

/** Payload stored on OperationRun.error_details.result for scraper ops. */
export interface OperationScraperRunResult {
  scraper_run_id?: string | null;
  adapter_key?: string | null;
  import_batch_id?: string | null;
  total_rows?: number | null;
  input_url?: string | null;
}

/** Focus target for reusing AdapterRunLogConsole on Operation Detail. */
export interface OperationScraperLiveLogTarget {
  scraperRunId: string;
  adapterKey: string;
}

/**
 * Reads the linked scraper run metadata from an OperationRun's error_details.result.
 * Does not guess "latest history" — only the run explicitly linked on this OperationRun.
 */
export function extractScraperResult(
  run: OperationRun | null | undefined,
): OperationScraperRunResult | null {
  if (!run?.error_details) return null;
  const result = run.error_details.result;
  if (!result || typeof result !== "object") return null;
  const payload = result as Record<string, unknown>;
  return {
    scraper_run_id:
      typeof payload.scraper_run_id === "string" ? payload.scraper_run_id : null,
    adapter_key: typeof payload.adapter_key === "string" ? payload.adapter_key : null,
    import_batch_id:
      typeof payload.import_batch_id === "string" ? payload.import_batch_id : null,
    total_rows: typeof payload.total_rows === "number" ? payload.total_rows : null,
    input_url: typeof payload.input_url === "string" ? payload.input_url : null,
  };
}

/**
 * Resolves the scraper run id + adapter key for the Operation Detail live log panel.
 * Returns null when this operation run has no linked scraper run (empty state).
 */
export function resolveOperationLiveLogTarget(
  run: OperationRun | null | undefined,
  typeConfigAdapterKey?: string | null,
): OperationScraperLiveLogTarget | null {
  const result = extractScraperResult(run);
  const scraperRunId = result?.scraper_run_id?.trim() || "";
  if (!scraperRunId) return null;

  const adapterKey =
    result?.adapter_key?.trim() ||
    (typeof typeConfigAdapterKey === "string" ? typeConfigAdapterKey.trim() : "") ||
    "";
  if (!adapterKey) return null;

  return { scraperRunId, adapterKey };
}
