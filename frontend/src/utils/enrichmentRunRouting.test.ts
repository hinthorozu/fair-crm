import { describe, expect, it } from "vitest";
import {
  buildEnrichmentRunDetailPath,
  buildScraperTestPath,
  resolveRunDetailPath,
} from "./enrichmentRunRouting";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "./enrichmentAdapter";

describe("resolveRunDetailPath", () => {
  const runId = "11111111-1111-1111-1111-111111111111";

  it("routes enrichment runs to run detail page", () => {
    const path = resolveRunDetailPath(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY, runId);
    expect(path).toContain("/data-integration/runs/");
    expect(path).toContain(runId);
    expect(path).not.toContain("scraper-test");
  });

  it("routes tuyap runs to scraper test page", () => {
    const path = resolveRunDetailPath("tuyap_old", runId);
    expect(path).toContain("/data-integration/scraper-test");
    expect(path).toContain(`run=${runId}`);
  });
});

describe("buildEnrichmentRunDetailPath", () => {
  it("includes adapter_key query param when provided", () => {
    const path = buildEnrichmentRunDetailPath("abc", CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY);
    expect(path).toBe(
      `/data-integration/runs/abc?adapter_key=${CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY}`,
    );
  });
});

describe("buildScraperTestPath", () => {
  it("builds scraper test query string", () => {
    expect(buildScraperTestPath("tuyap_old", "run-1")).toBe(
      "/data-integration/scraper-test?adapter_key=tuyap_old&run=run-1",
    );
  });
});
