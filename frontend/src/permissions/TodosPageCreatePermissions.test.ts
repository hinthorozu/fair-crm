import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodosPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todos page create permission", () => {
  it("uses canonical todos create permission", () => {
    expect(source).toContain('const canCreate = canPerformTodoAction(grantedPermissions, "create")');
  });

  it("fails closed before creating a todo", () => {
    expect(source).toContain("const handleCreate = async (values: TodoFormValues) => {\n    if (!canCreate) return;");
  });
});
