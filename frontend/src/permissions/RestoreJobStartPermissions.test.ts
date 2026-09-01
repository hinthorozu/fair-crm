import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../components/admin/RestoreJobDetailModal.tsx", import.meta.url),
  "utf8",
);

describe("RestoreJobDetailModal start permission", () => {
  it("fails closed before starting a restore job", () => {
    expect(source).toContain("if (!canStart) return;");
    expect(source).toContain("const canStart = React.useMemo(() => canCreateAdminBackupOperation(), []);");
  });

  it("hides the start action without backup create permission", () => {
    expect(source).toContain('uiStatus === "queued" && canStart');
  });
});
