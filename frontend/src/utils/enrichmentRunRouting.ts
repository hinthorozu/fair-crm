import { isCustomerContactEnrichmentAdapter } from "./enrichmentAdapter";

export function buildEnrichmentRunDetailPath(runId: string, adapterKey?: string): string {
  const params = new URLSearchParams();
  if (adapterKey) {
    params.set("adapter_key", adapterKey);
  }
  const qs = params.toString();
  return `/data-integration/runs/${encodeURIComponent(runId)}${qs ? `?${qs}` : ""}`;
}

export function buildScraperTestPath(adapterKey?: string, runId?: string): string {
  const params = new URLSearchParams();
  if (adapterKey) params.set("adapter_key", adapterKey);
  if (runId) params.set("run", runId);
  const qs = params.toString();
  return `/data-integration/scraper-test${qs ? `?${qs}` : ""}`;
}

export function resolveRunDetailPath(adapterKey: string, runId: string): string {
  if (isCustomerContactEnrichmentAdapter(adapterKey)) {
    return buildEnrichmentRunDetailPath(runId, adapterKey);
  }
  return buildScraperTestPath(adapterKey, runId);
}
