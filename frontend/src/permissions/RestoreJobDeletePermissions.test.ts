import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../components/admin/RestoreJobDetailModal.tsx", import.meta.url),
  "utf8",
);

describe("RestoreJobDetailModal delete permission", () => {
  it("fails closed before deleting a restore job", () => {
    expect(source).toContain("if (!canDelete) return;");
    expect(source).toContain("const canDelete = React.useMemo(() => canDeleteAdminBackupOperation(), []);");
  });

  it("hides the delete action without backup delete permission", () => {
    expect(source).toContain("{canDelete ? (");
  });
});
