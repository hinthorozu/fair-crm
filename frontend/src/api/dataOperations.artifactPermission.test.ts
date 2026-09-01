import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./dataOperations.ts", import.meta.url), "utf8");

function functionSource(name: string): string {
  const start = source.indexOf(`export async function ${name}`);
  expect(start).toBeGreaterThanOrEqual(0);
  return source.slice(start, source.indexOf("\n}\n", start) + 3);
}

describe("data operation artifact client permissions", () => {
  it("uses execute-only for analyzed dataset export", () => {
    const datasetExport = functionSource("exportDataOperationDatasetCustomers");
    expect(datasetExport).toContain("requireDataOperationExecutePermission();");
    expect(datasetExport).not.toContain("requireDataOperationArtifactPermissions();");
    expect(datasetExport.indexOf("requireDataOperationExecutePermission();")).toBeLessThan(
      datasetExport.indexOf("fetchWithTimeout("),
    );
  });

  it("uses execute-only for duplicate dataset export", () => {
    const duplicateExport = functionSource("exportDataOperationDuplicateCustomers");
    expect(duplicateExport).toContain("requireDataOperationExecutePermission();");
    expect(duplicateExport).not.toContain("requireDataOperationArtifactPermissions();");
    expect(duplicateExport.indexOf("requireDataOperationExecutePermission();")).toBeLessThan(
      duplicateExport.indexOf("fetchWithTimeout("),
    );
  });

  it("keeps output-file download on its existing artifact boundary in this focused fix", () => {
    const fileDownload = functionSource("downloadDataOperationFile");
    expect(fileDownload).toContain("requireDataOperationArtifactPermissions();");
    expect(fileDownload.indexOf("requireDataOperationArtifactPermissions();")).toBeLessThan(
      fileDownload.indexOf("fetchWithTimeout("),
    );
  });
});
