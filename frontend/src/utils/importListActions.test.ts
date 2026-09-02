import { describe, expect, it } from "vitest";
import { importBatchListPrimaryActions } from "./importListActions";

describe("importBatchListPrimaryActions", () => {
  it("shows analyze only before analysis", () => {
    expect(importBatchListPrimaryActions("received")).toEqual(["analyze"]);
    expect(importBatchListPrimaryActions("mapping_completed")).toEqual(["analyze"]);
    expect(importBatchListPrimaryActions("mapped")).toEqual(["analyze"]);
    expect(importBatchListPrimaryActions("analysis_failed")).toEqual(["analyze"]);
  });

  it("offers reanalyze and continue after analysis completes", () => {
    for (const status of ["decision_required", "analyzed", "previewed"] as const) {
      expect(importBatchListPrimaryActions(status)).toEqual(["reanalyze", "continue"]);
    }
  });

  it("shows in-progress state without continue or analyze", () => {
    for (const status of ["analysis_queued", "analyzing", "applying"] as const) {
      expect(importBatchListPrimaryActions(status)).toEqual(["in_progress"]);
    }
  });

  it("setup resume shows continue only", () => {
    for (const status of ["uploaded", "sheet_selected", "header_configured"] as const) {
      expect(importBatchListPrimaryActions(status)).toEqual(["continue"]);
    }
  });

  it("terminal batches have no primary actions", () => {
    for (const status of ["completed", "applied", "failed", "cancelled"] as const) {
      expect(importBatchListPrimaryActions(status)).toEqual([]);
    }
  });
});
