import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DataOperationAnalyzeResultPage.tsx", import.meta.url),
  "utf8",
);

describe("DataOperationAnalyzeResultPage execute permissions", () => {
  it("requires admin data-operation execute permission for result mutations", () => {
    expect(source).toContain(
      'const DATA_OPERATIONS_EXECUTE_PERMISSION = "fair_crm.admin.data_operations.execute";',
    );
    expect(source).toContain("const canExecuteDataOperations = can(DATA_OPERATIONS_EXECUTE_PERMISSION);");
    expect(source).toContain("if (!canExecuteDataOperations || !assignFairId || selectedCount === 0) return;");
    expect(source).toContain("if (!canExecuteDataOperations || selectedCount === 0) return;");
    expect(source).toContain("{canExecuteDataOperations ? (");
    expect(source).toContain("open={assignModalOpen && canExecuteDataOperations}");
    expect(source).toContain("open={deleteModalOpen && canExecuteDataOperations}");
  });

  it("keeps export outside the execute gate", () => {
    expect(source).toContain("onClick={() => void handleExport()}");
  });
});
