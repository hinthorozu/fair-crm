import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/ImportWizardPage.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./importPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Import wizard execute permission", () => {
  it("uses canonical imports execute permission", () => {
    expect(permissionSource).toContain('IMPORT_PERMISSION_EXECUTE = "fair_crm.imports.execute"');
    expect(source).toContain("const canExecute = can(IMPORT_PERMISSION_EXECUTE)");
  });

  it("fails closed for applying decisions", () => {
    expect(source).toContain("const handleApplyDecisions = async () => {\n    if (!canExecute) return;");
    expect(source).toContain("!canExecute\n            || isImportDecisionBusy");
  });
});
