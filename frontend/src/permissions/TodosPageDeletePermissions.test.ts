import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodosPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todos page delete permission", () => {
  it("maps archive and delete actions to canonical todos delete permission", () => {
    expect(source).toContain('const canArchive = canPerformTodoAction(grantedPermissions, "archive")');
    expect(source).toContain('const canDelete = canPerformTodoAction(grantedPermissions, "delete")');
  });

  it("fails closed before archiving a todo", () => {
    expect(source).toContain("const handleArchive = async (todo: Todo) => {\n    if (!canArchive) return;");
  });

  it("fails closed before deleting a todo", () => {
    expect(source).toContain("const handleDelete = async (todo: Todo) => {\n    if (!canDelete) return;");
  });
});
