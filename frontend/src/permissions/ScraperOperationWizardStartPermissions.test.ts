import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/ScraperOperationWizardPage.tsx", import.meta.url),
  "utf8",
);

describe("ScraperOperationWizardPage start permissions", () => {
  it("requires operation create and execute permissions for immediate start", () => {
    expect(source).toContain(
      "const canStart = can(PERMISSION_OPERATIONS_CREATE) && can(OPERATION_EXECUTE);",
    );
    expect(source).toContain("start_immediately: true");
  });

  it("fails closed before creating the scraper operation", () => {
    expect(source).toContain("const submit = async () => {");
    expect(source).toContain("if (!canStart) return;");
    expect(source).toContain("const created = await createOperation(buildPayload());");
  });

  it("hides the final start affordance without both permissions", () => {
    expect(source).toContain(") : canStart ? (");
    expect(source).toContain("{operationLabels.startAutomation}");
  });
});
