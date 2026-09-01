import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DataOperationsPage.tsx", import.meta.url),
  "utf8",
);

describe("DataOperationsPage download permissions", () => {
  it("uses the backend canonical data-operations read permission", () => {
    expect(source).toContain(
      'const DATA_OPERATIONS_READ = "fair_crm.admin.data_operations.read";',
    );
    expect(source).toContain("const canDownload = can(DATA_OPERATIONS_READ);");
  });

  it("fails closed before downloading an output file", () => {
    expect(source).toContain("if (!canDownload) return;");
    expect(source).toContain("await downloadDataOperationFile(run.id, fileId, fileName);");
  });

  it("hides download affordances without read permission", () => {
    expect(source).toContain(
      "{canDownload && downloadsFrom?.output_files && downloadsFrom.output_files.length > 0 && (",
    );
    expect(source).toContain(
      "onClick={() => void handleDownload(downloadsFrom, file.id, file.file_name)}",
    );
  });
});
