import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DatabaseBackupsPage.tsx", import.meta.url),
  "utf8",
);

describe("DatabaseBackupsPage download permission", () => {
  it("fails closed before downloading a backup", () => {
    expect(source).toContain("if (!canDownload) return;");
    expect(source).toContain("const canDownload = React.useMemo(() => canExecuteAdminBackupOperation(), []);");
  });

  it("hides the download action without backup execute permission", () => {
    expect(source).toContain("{handlers.canDownload ? (");
    expect(source).toContain("canDownload,");
  });
});
