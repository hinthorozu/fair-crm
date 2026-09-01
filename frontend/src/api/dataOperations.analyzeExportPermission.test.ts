import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./dataOperations.ts", import.meta.url), "utf8");

describe("analyze dataset export client permission", () => {
  it("requires execute only before network activity", () => {
    const start = source.indexOf("export async function exportDataOperationDatasetCustomers");
    const end = source.indexOf("\n}\n", start) + 3;
    const exportSource = source.slice(start, end);

    expect(exportSource).toContain("requireDataOperationExecutePermission();");
    expect(exportSource).not.toContain("requireDataOperationArtifactPermissions();");
    expect(exportSource.indexOf("requireDataOperationExecutePermission();")).toBeLessThan(
      exportSource.indexOf("fetchWithTimeout("),
    );
  });
});
