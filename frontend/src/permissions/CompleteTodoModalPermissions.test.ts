import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/todos/CompleteTodoModal.tsx", import.meta.url)),
  "utf8",
);

describe("Complete todo permission", () => {
  it("uses canonical todos update permission", () => {
    expect(source).toContain('const canUpdate = canPerformTodoAction(grantedPermissions, "update")');
  });

  it("fails closed before completing a todo", () => {
    expect(source).toContain("event.preventDefault();\n    if (!canUpdate) return;");
  });

  it("does not render the submit action without update permission", () => {
    expect(source).toContain('{canUpdate ? (');
  });
});
