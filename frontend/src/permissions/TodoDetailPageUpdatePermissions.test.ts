import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodoDetailPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todo detail update permission", () => {
  it("uses canonical todos update permission", () => {
    expect(source).toContain('const canUpdate = canPerformTodoAction(grantedPermissions, "update")');
  });

  it("fails closed before saving todo edits", () => {
    expect(source).toContain("const handleEditSubmit = async (values: TodoFormValues) => {\n    if (!canUpdate) return;");
  });

  it("does not mount the edit modal without update permission", () => {
    expect(source).toContain('{editOpen && canUpdate ? (');
  });
});
