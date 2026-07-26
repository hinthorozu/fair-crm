import { describe, expect, it } from "vitest";
import type { Operation } from "../types/operation";
import {
  extractOperationFairIds,
  formatOperationFairSourceLabel,
} from "./operationFairSource";

function baseOperation(overrides: Partial<Operation> = {}): Operation {
  return {
    id: "op-1",
    organization_id: "org-1",
    operation_type: "bulk_email",
    title: "Toplu e-posta",
    description: null,
    status: "completed",
    priority: "normal",
    source_kind: "fair",
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

describe("extractOperationFairIds", () => {
  it("reads fair ids from bulk_email source_ids", () => {
    expect(
      extractOperationFairIds(
        baseOperation({
          source_ids: ["fair-a", "fair-b"],
          type_config: { fair_ids: ["fair-a", "fair-b"] },
        }),
      ),
    ).toEqual(["fair-a", "fair-b"]);
  });

  it("falls back to type_config.fair_ids", () => {
    expect(
      extractOperationFairIds(
        baseOperation({
          source_kind: "manual_selection",
          type_config: { fair_ids: ["fair-x"] },
        }),
      ),
    ).toEqual(["fair-x"]);
  });
});

describe("formatOperationFairSourceLabel", () => {
  it("shows the real fair name for a single fair", () => {
    expect(formatOperationFairSourceLabel("Fuar", ["Food İst"], 1)).toBe("Food İst");
  });

  it("joins multiple real fair names", () => {
    expect(
      formatOperationFairSourceLabel(
        "Fuar",
        ["Food İst", "İstanbul İplik Fuarı"],
        2,
      ),
    ).toBe("Food İst, İstanbul İplik Fuarı");
  });

  it("does not use Fuar (n) when names resolve", () => {
    const label = formatOperationFairSourceLabel("Fuar", ["Food İst"], 1);
    expect(label).not.toContain("Fuar (");
    expect(label).toBe("Food İst");
  });

  it("falls back to Fuar (n) when names cannot be resolved", () => {
    expect(formatOperationFairSourceLabel("Fuar", [], 1)).toBe("Fuar (1)");
    expect(formatOperationFairSourceLabel("Fuar", ["  ", ""], 2)).toBe("Fuar (2)");
  });

  it("dedupes repeated names while preserving order", () => {
    expect(
      formatOperationFairSourceLabel("Fuar", ["Food İst", "Food İst", "Expo"], 3),
    ).toBe("Food İst, Expo");
  });
});
