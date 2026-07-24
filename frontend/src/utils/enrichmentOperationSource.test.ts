import { describe, expect, it } from "vitest";
import { scraperLabels } from "../labels/scraperLabels";
import type { Operation } from "../types/operation";
import {
  buildEnrichmentSourceFilterRows,
  extractEnrichmentFairIds,
} from "./enrichmentOperationSource";

function baseOperation(overrides: Partial<Operation> = {}): Operation {
  return {
    id: "op-1",
    organization_id: "org-1",
    operation_type: "enrichment",
    title: "Müşteri Zenginleştirme",
    description: null,
    status: "completed",
    priority: "normal",
    source_kind: "customer",
    source_ids: [],
    source_config: {},
    type_config: {},
    run_settings: {},
    related_todo_id: null,
    latest_run_id: null,
    latest_run: null,
    capabilities: {},
    created_at: "2026-07-24T00:00:00Z",
    updated_at: "2026-07-24T00:00:00Z",
    created_by: "user-1",
    updated_by: null,
    ...overrides,
  };
}

describe("extractEnrichmentFairIds", () => {
  it("reads multi fair ids from source_ids", () => {
    const ids = extractEnrichmentFairIds(
      baseOperation({
        source_kind: "fair",
        source_ids: ["fair-a", "fair-b"],
        type_config: { fair_ids: ["fair-a", "fair-b"] },
      }),
    );
    expect(ids).toEqual(["fair-a", "fair-b"]);
  });

  it("falls back to type_config.fair_ids when source is customer", () => {
    const ids = extractEnrichmentFairIds(
      baseOperation({
        source_kind: "customer",
        type_config: { fair_ids: ["fair-x"] },
      }),
    );
    expect(ids).toEqual(["fair-x"]);
  });
});

describe("buildEnrichmentSourceFilterRows", () => {
  it("shows fair names and only applied filters with Turkish match labels", () => {
    const rows = buildEnrichmentSourceFilterRows(
      baseOperation({
        source_kind: "fair",
        source_ids: ["1", "2"],
        type_config: {
          company_name: "SDK",
          company_name_match: "contains",
          address_contains: "İstanbul",
          limit: 50,
        },
      }),
      ["İSTANBUL KİTAP FUARI", "EXPOMED EURASIA"],
    );

    expect(rows.map((row) => row.label)).toEqual([
      scraperLabels.enrichmentRunFairPlural,
      scraperLabels.enrichmentRunCompanyName,
      scraperLabels.enrichmentRunCompanyNameMatch,
      scraperLabels.enrichmentRunAddress,
      scraperLabels.enrichmentRunLimit,
    ]);
    expect(rows[0].values).toEqual(["İSTANBUL KİTAP FUARI", "EXPOMED EURASIA"]);
    expect(rows.find((row) => row.key === "company_name_match")?.values).toEqual([
      scraperLabels.enrichmentRunCompanyNameMatchContains,
    ]);
  });

  it("hides empty filters and does not invent a fair row", () => {
    const rows = buildEnrichmentSourceFilterRows(
      baseOperation({
        type_config: {
          company_name: "SDK",
          company_name_match: "starts_with",
          address_contains: "",
          limit: null,
        },
      }),
      [],
    );
    expect(rows.map((row) => row.key)).toEqual(["company_name", "company_name_match"]);
    expect(rows.find((row) => row.key === "company_name_match")?.values).toEqual([
      scraperLabels.enrichmentRunCompanyNameMatchStartsWith,
    ]);
  });

  it("uses singular Fuar label for one fair", () => {
    const rows = buildEnrichmentSourceFilterRows(
      baseOperation({ source_kind: "fair", source_ids: ["1"] }),
      ["FOOD İSTANBUL"],
    );
    expect(rows).toEqual([
      {
        key: "fairs",
        label: scraperLabels.enrichmentRunFairFilter,
        values: ["FOOD İSTANBUL"],
      },
    ]);
  });
});
