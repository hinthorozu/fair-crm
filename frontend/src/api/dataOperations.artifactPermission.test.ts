import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./dataOperations.ts", import.meta.url), "utf8");

describe("data operation artifact client permissions", () => {
  it("requires both effective backend permissions", () => {
    expect(source).toContain(
      'const DATA_OPERATIONS_READ = "fair_crm.admin.data_operations.read";',
    );
    expect(source).toContain(
      'const DATA_OPERATIONS_EXECUTE = "fair_crm.admin.data_operations.execute";',
    );
    expect(source).toContain("!permissions.has(DATA_OPERATIONS_READ)");
    expect(source).toContain("!permissions.has(DATA_OPERATIONS_EXECUTE)");
  });

  it("fails closed before each direct artifact fetch", () => {
    const datasetExport = source.indexOf("export async function exportDataOperationDatasetCustomers");
    const duplicateExport = source.indexOf("export async function exportDataOperationDuplicateCustomers");
    const fileDownload = source.indexOf("export async function downloadDataOperationFile");

    for (const start of [datasetExport, duplicateExport, fileDownload]) {
      expect(start).toBeGreaterThanOrEqual(0);
      const artifactFunction = source.slice(start, source.indexOf("\n}\n", start) + 3);
      expect(artifactFunction).toContain("requireDataOperationArtifactPermissions();");
      expect(artifactFunction.indexOf("requireDataOperationArtifactPermissions();")).toBeLessThan(
        artifactFunction.indexOf("fetchWithTimeout("),
      );
    }
  });
});
