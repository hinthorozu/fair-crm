import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/todos/TodoForm.tsx", import.meta.url)),
  "utf8",
);

describe("Todo form checklist permission", () => {
  it("uses canonical todos update permission for checklist management", () => {
    expect(source).toContain('import { TODO_PERMISSION_UPDATE } from "../../permissions/todoPermissions";');
    expect(source).toContain("hasGrantedCorePermission(grantedPermissions, TODO_PERMISSION_UPDATE)");
  });

  it("fails closed by stripping checklist values without update permission", () => {
    expect(source).toContain("await onSubmit(canManageSteps ? values : { ...values, steps: [] });");
  });

  it("does not expose or auto-create checklist steps without update permission", () => {
    expect(source).toContain('canManageSteps && category === "stand_work"');
    expect(source).toContain("{canManageSteps ? (\n          <TodoStepFieldList");
  });
});
