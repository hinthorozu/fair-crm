import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodosPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todos create checklist permission", () => {
  it("keeps todo creation on the create permission", () => {
    expect(source).toContain("if (!canCreate) return;");
  });

  it("requires update permission before the checklist mutation", () => {
    expect(source).toContain("if (canUpdate && stepPayload.length > 0) {");
    expect(source).toContain("await replaceTodoSteps(created.id, { steps: stepPayload });");
  });
});
