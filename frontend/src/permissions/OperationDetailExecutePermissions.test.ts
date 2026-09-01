import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/OperationDetailPageLegacy.tsx", import.meta.url),
  "utf8",
);

describe("OperationDetailPage execute permissions", () => {
  it("keeps generic operation execute at start and cancel mutation boundaries", () => {
    expect(source.match(/if \(!canExecute\) return;/g)).toHaveLength(2);
    expect(source).toContain("await startOperation(operationId);");
    expect(source).toContain("await cancelOperation(operationId);");
    expect(source).toContain("const canStart =\n    canExecute &&");
    expect(source).toContain("const canCancel =\n    canExecute &&");
  });

  it("uses fair email execute at every bulk email retry boundary", () => {
    expect(source).toContain(
      'import { FAIR_EMAIL_PERMISSION_EXECUTE } from "../permissions/fairEmailPermissions";',
    );
    expect(source).toContain("const canRetryBulkEmail = can(FAIR_EMAIL_PERMISSION_EXECUTE);");
    expect(source).toContain(
      "const handleRetryFailed = async () => {\n    if (!canRetryBulkEmail) return;",
    );
    expect(source).toContain("const canRetryFailed =\n    canRetryBulkEmail &&");
    expect(source).toContain("retryConfirmOpen && canRetryBulkEmail");
    expect(source).toContain("await retryBulkEmailOperationFailed(operationId);");
  });
});
