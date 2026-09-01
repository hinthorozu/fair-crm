import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodoDetailPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todo detail worklist save permission", () => {
  it("uses canonical todos update permission", () => {
    expect(source).toContain(
      'const canUpdate = canPerformTodoAction(grantedPermissions, "update")',
    );
  });

  it("fails closed before recording a worklist activity", () => {
    expect(source).toContain(
      "const handleSaveActivity = async (payload: RecordTodoWorklistActivityPayload) => {\n    if (!canUpdate || !selectedCustomerId) return;",
    );
  });
});
