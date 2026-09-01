import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/ScraperOperationWizardPage.tsx", import.meta.url),
  "utf8",
);

describe("ScraperOperationWizardPage start permissions", () => {
  it("requires the canonical scraper execute permission for immediate start", () => {
    expect(source).toContain(
      'import { SCRAPER_PERMISSION_EXECUTE } from "../permissions/scraperPermissions";',
    );
    expect(source).toContain("const canStart = can(SCRAPER_PERMISSION_EXECUTE);");
    expect(source).toContain('operation_type: "scraper" as const');
    expect(source).toContain("start_immediately: true");
    expect(source).not.toContain("PERMISSION_OPERATIONS_CREATE");
    expect(source).not.toContain("OPERATION_EXECUTE");
  });

  it("fails closed before creating the scraper operation", () => {
    expect(source).toContain("const submit = async () => {");
    expect(source).toContain("if (!canStart) return;");
    expect(source).toContain("const created = await createOperation(buildPayload());");
  });

  it("hides the final start affordance without execute permission", () => {
    expect(source).toContain(") : canStart ? (");
    expect(source).toContain("{operationLabels.startAutomation}");
  });
});
