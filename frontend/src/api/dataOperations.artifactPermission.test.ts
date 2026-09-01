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

  it("keeps the remaining artifact boundary unchanged for this focused fix", () => {
    const duplicateExport = functionSource("exportDataOperationDuplicateCustomers");
    const fileDownload = functionSource("downloadDataOperationFile");

    for (const artifactFunction of [duplicateExport, fileDownload]) {
      expect(artifactFunction).toContain("requireDataOperationArtifactPermissions();");
      expect(artifactFunction.indexOf("requireDataOperationArtifactPermissions();")).toBeLessThan(
        artifactFunction.indexOf("fetchWithTimeout("),
      );
    }
  });
});
