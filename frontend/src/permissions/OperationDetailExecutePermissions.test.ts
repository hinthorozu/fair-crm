import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/OperationDetailPageLegacy.tsx", import.meta.url),
  "utf8",
);

describe("OperationDetailPage execute permissions", () => {
  it("fails closed at start, cancel, and retry mutation boundaries", () => {
    expect(source.match(/if \(!canExecute\) return;/g)).toHaveLength(3);
    expect(source).toContain("await startOperation(operationId);");
    expect(source).toContain("await cancelOperation(operationId);");
    expect(source).toContain("await retryBulkEmailOperationFailed(operationId);");
  });

  it("gates execute affordances and retry confirmation", () => {
    expect(source).toContain("const canExecute = can(OPERATION_EXECUTE);");
    expect(source).toContain("const canStart =\n    canExecute &&");
    expect(source).toContain("const canCancel =\n    canExecute &&");
    expect(source).toContain("const canRetryFailed =\n    canExecute &&");
    expect(source).toContain("retryConfirmOpen && canExecute");
  });
});
