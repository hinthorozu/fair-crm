import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodosPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todos create quote navigation permission", () => {
  it("reuses the canonical quote editor navigation helper", () => {
    expect(source).toContain(
      'import { canOpenTodoQuoteAction } from "../permissions/todoQuoteActionPermissions";',
    );
    expect(source).toContain("const canOpenQuote = canOpenTodoQuoteAction(grantedPermissions);");
  });

  it("does not auto-open quote editor without the canonical read capability", () => {
    expect(source).toContain(
      'if (canOpenQuote && created.category === "teklif") onOpenQuote?.(created.id);',
    );
  });
});
