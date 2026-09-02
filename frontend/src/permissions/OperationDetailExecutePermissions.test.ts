import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/OperationDetailPageLegacy.tsx", import.meta.url),
  "utf8",
);

describe("OperationDetailPage execute permissions", () => {
  it("uses fair email execute for Bulk Email Start while preserving generic Start fallback", () => {
    expect(source).toContain(
      'import { FAIR_EMAIL_PERMISSION_EXECUTE } from "../permissions/fairEmailPermissions";',
    );
    expect(source).toContain("const canStartBulkEmail = can(FAIR_EMAIL_PERMISSION_EXECUTE);");
    expect(source).toContain("const canStartOperation = isBulkEmailOp");
    expect(source).toContain("? canStartBulkEmail");
    expect(source).toContain(": isEnrichmentOp");
    expect(source).toContain(": isScraperOp");
    expect(source).toContain(": canExecute;");
    expect(source).toContain("const handleStart = async () => {\n    if (!canStartOperation) return;");
    expect(source).toContain("const canStart =\n    canStartOperation &&");
    expect(source).toContain("await startOperation(operationId);");
  });

  it("uses scraper execute for Enrichment Start", () => {
    expect(source).toContain(
      'import { SCRAPER_PERMISSION_EXECUTE } from "../permissions/scraperPermissions";',
    );
    expect(source).toContain("const canStartEnrichment = can(SCRAPER_PERMISSION_EXECUTE);");
    expect(source).toContain(
      'const isEnrichmentOp = detail?.operation.operation_type === "enrichment";',
    );
    expect(source).toContain("? canStartEnrichment");
  });

  it("uses scraper execute for Scraper Start", () => {
    expect(source).toContain("const canStartScraper = can(SCRAPER_PERMISSION_EXECUTE);");
    expect(source).toContain(
      'const isScraperOp = detail?.operation.operation_type === "scraper";',
    );
    expect(source).toContain("? canStartScraper");
  });

  it("keeps operation execute at the Cancel mutation boundary", () => {
    expect(source).toContain("const handleCancel = async () => {\n    if (!canExecute) return;");
    expect(source).toContain("await cancelOperation(operationId);");
    expect(source).toContain("const canCancel =\n    canExecute &&");
  });

  it("uses fair email execute at every bulk email retry boundary", () => {
    expect(source).toContain("const canRetryBulkEmail = can(FAIR_EMAIL_PERMISSION_EXECUTE);");
    expect(source).toContain("const handleRetryFailed = async () => {\n    if (!canRetryBulkEmail) return;");
    expect(source).toContain("const canRetryFailed =\n    canRetryBulkEmail &&");
    expect(source).toContain("retryConfirmOpen && canRetryBulkEmail");
    expect(source).toContain("await retryBulkEmailOperationFailed(operationId);");
  });
});
