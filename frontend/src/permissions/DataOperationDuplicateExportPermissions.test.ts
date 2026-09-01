import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DataOperationDuplicateResultPage.tsx", import.meta.url),
  "utf8",
);

describe("DataOperationDuplicateResultPage export permissions", () => {
  it("uses the data-operations execute permission for export actions", () => {
    expect(source).toContain(
      'const DATA_OPERATIONS_EXECUTE_PERMISSION = "fair_crm.admin.data_operations.execute";',
    );
    expect(source).toContain(
      "const canExecuteDataOperations = can(DATA_OPERATIONS_EXECUTE_PERMISSION);",
    );
  });

  it("fails closed before exporting duplicate customers", () => {
    expect(source).toContain("const handleExport = async () => {");
    expect(source).toContain("if (!canExecuteDataOperations) return;");
    expect(source).toContain("await exportDataOperationDuplicateCustomers(runId, {");
  });

  it("hides the export affordance without execute permission", () => {
    expect(source).toContain("{canExecuteDataOperations ? (");
    expect(source).toContain("onClick={() => void handleExport()}");
  });
});
