import { describe, expect, it } from "vitest";
import {
  formatImportLastAnalyzedAt,
  hasImportBatchBeenAnalyzed,
  importAnalysisStatusLabel,
} from "./importAnalysisDisplay";

describe("importAnalysisDisplay", () => {
  it("uses analyzed_at when present", () => {
    const batch = {
      analyzed_at: "2026-07-01T10:00:00Z",
      status: "decision_required" as const,
    };
    expect(hasImportBatchBeenAnalyzed(batch)).toBe(true);
    expect(importAnalysisStatusLabel(batch)).toBe("Analiz Edildi");
    expect(formatImportLastAnalyzedAt(batch.analyzed_at)).not.toBe("—");
  });

  it("infers analyzed state for legacy batches without timestamp", () => {
    const batch = { analyzed_at: null, status: "decision_required" as const };
    expect(hasImportBatchBeenAnalyzed(batch)).toBe(true);
    expect(formatImportLastAnalyzedAt(null)).toBe("—");
  });

  it("shows not analyzed before first run", () => {
    const batch = { analyzed_at: null, status: "received" as const };
    expect(hasImportBatchBeenAnalyzed(batch)).toBe(false);
    expect(importAnalysisStatusLabel(batch)).toBe("Analiz Edilmedi");
  });
});
