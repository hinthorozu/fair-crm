import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodosPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todos page update permission", () => {
  it("uses canonical todos update permission", () => {
    expect(source).toContain('const canUpdate = canPerformTodoAction(grantedPermissions, "update")');
  });

  it("fails closed before updating a todo", () => {
    expect(source).toContain("const handleUpdate = async (values: TodoFormValues) => {\n    if (!canUpdate) return;");
  });
});
