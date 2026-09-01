import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DatabaseBackupsPage.tsx", import.meta.url),
  "utf8",
);

describe("DatabaseBackupsPage delete permission", () => {
  it("fails closed before deleting a backup", () => {
    expect(source).toContain("if (!canDelete || !deleteTarget) return;");
    expect(source).toContain("const canDelete = React.useMemo(() => canDeleteAdminBackupOperation(), []);");
  });

  it("hides backup delete surfaces without delete permission", () => {
    expect(source).toContain("{canDelete ? (");
    expect(source).toContain("deleteTarget && canDelete");
  });
});
