import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(
  new URL("../pages/DataOperationsPage.tsx", import.meta.url),
  "utf8",
);
const clientSource = readFileSync(
  new URL("../api/dataOperationDownload.ts", import.meta.url),
  "utf8",
);

describe("DataOperationsPage download permissions", () => {
  it("uses only the canonical data-operations execute permission", () => {
    expect(pageSource).toContain(
      'const DATA_OPERATIONS_EXECUTE = "fair_crm.admin.data_operations.execute";',
    );
    expect(pageSource).toContain("const canDownload = can(DATA_OPERATIONS_EXECUTE);");
    expect(pageSource).not.toContain(
      "const canDownload = can(DATA_OPERATIONS_READ) && can(DATA_OPERATIONS_EXECUTE);",
    );
  });

  it("fails closed before downloading an output file", () => {
    expect(pageSource).toContain("if (!canDownload) return;");
    expect(pageSource).toContain("await downloadDataOperationFile(run.id, fileId, fileName);");
    expect(clientSource).toContain("if (!permissions.has(DATA_OPERATIONS_EXECUTE)) {");
  });

  it("hides download affordances unless execute is granted", () => {
    expect(pageSource).toContain(
      "{canDownload && downloadsFrom?.output_files && downloadsFrom.output_files.length > 0 && (",
    );
    expect(pageSource).toContain(
      "onClick={() => void handleDownload(downloadsFrom, file.id, file.file_name)}",
    );
  });
});
