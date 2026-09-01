import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/dashboard/DashboardNewTodoModal.tsx", import.meta.url)),
  "utf8",
);

describe("DashboardNewTodoModal permissions", () => {
  it("uses the canonical todo create permission", () => {
    expect(source).toContain("TODO_PERMISSION_CREATE");
    expect(source).toContain("getGrantedCorePermissions().has(TODO_PERMISSION_CREATE)");
  });

  it("fails closed before creating a todo", () => {
    expect(source).toContain("const handleCreate = async (values: TodoFormValues) => {\n    if (!canCreateTodo) return;");
  });

  it("hides the save affordance without create permission", () => {
    expect(source).toContain("{canCreateTodo ? (");
  });
});
