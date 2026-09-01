import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DatabaseBackupsPage.tsx", import.meta.url),
  "utf8",
);

describe("DatabaseBackupsPage create/restore permissions", () => {
  it("fails closed before create and restore mutations", () => {
    expect(source).toContain("if (!canCreate) return;");
    expect(source).toContain("if (!canCreate || !restoreTarget) return;");
    expect(source).toContain("if (!canCreate || !restoreUploadFile) return;");
  });

  it("hides create and restore surfaces without backup create permission", () => {
    expect(source).toContain("showCreateModal && canCreate");
    expect(source).toContain("restoreTarget && canCreate");
    expect(source).toContain("showRestoreUploadModal && canCreate");
  });
});
