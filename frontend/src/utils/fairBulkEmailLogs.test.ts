import { describe, expect, it } from "vitest";
import {
  fairEmailBatchStatusLabel,
  fairEmailBatchStatusVariant,
  isActiveBatchStatus,
} from "./fairBulkEmailLogs";

describe("fairBulkEmailLogs", () => {
  it("detects active batch statuses for polling", () => {
    expect(isActiveBatchStatus("queued")).toBe(true);
    expect(isActiveBatchStatus("processing")).toBe(true);
    expect(isActiveBatchStatus("completed")).toBe(false);
  });

  it("maps batch status labels and variants", () => {
    expect(fairEmailBatchStatusLabel("completed_with_errors")).toBe("Kısmen başarısız");
    expect(fairEmailBatchStatusVariant("completed_with_errors")).toBe("warning");
    expect(fairEmailBatchStatusVariant("completed")).toBe("success");
  });
});
