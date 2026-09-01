import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DataOperationAnalyzeResultPage.tsx", import.meta.url),
  "utf8",
);

describe("DataOperationAnalyzeResultPage export permissions", () => {
  it("uses the data-operations execute permission for export actions", () => {
    expect(source).toContain(
      'const DATA_OPERATIONS_EXECUTE_PERMISSION = "fair_crm.admin.data_operations.execute";',
    );
    expect(source).toContain(
      "const canExecuteDataOperations = can(DATA_OPERATIONS_EXECUTE_PERMISSION);",
    );
  });

  it("fails closed before exporting the analyzed customer dataset", () => {
    expect(source).toContain("const handleExport = async () => {");
    expect(source).toContain("if (!canExecuteDataOperations) return;");
    expect(source).toContain("await exportDataOperationDatasetCustomers(runId, {");
  });

  it("keeps the export affordance inside the execute-permission action group", () => {
    const gatedActions = source.indexOf("{canExecuteDataOperations ? (");
    const exportClick = source.indexOf("onClick={() => void handleExport()}");
    const gateClose = source.indexOf(") : null}", gatedActions);

    expect(gatedActions).toBeGreaterThanOrEqual(0);
    expect(exportClick).toBeGreaterThan(gatedActions);
    expect(gateClose).toBeGreaterThan(exportClick);
  });
});
