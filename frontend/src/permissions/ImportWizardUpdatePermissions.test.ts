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

describe("Import wizard update permission", () => {
  it("uses canonical imports update permission", () => {
    expect(permissionSource).toContain('IMPORT_PERMISSION_UPDATE = "fair_crm.imports.update"');
    expect(source).toContain("const canUpdate = can(IMPORT_PERMISSION_UPDATE)");
  });

  it("fails closed for update mutations", () => {
    expect(source.match(/if \(!canUpdate\) return;/g)?.length ?? 0).toBeGreaterThanOrEqual(5);
    expect(source).toContain("renderMergePreviewList(!decisionBusy && canUpdate)");
    expect(source).toContain('["sheet", "header", "mapping"].includes(currentStep) && !canUpdate');
  });
});
