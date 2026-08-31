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

describe("Import wizard create permission", () => {
  it("uses canonical imports create permission", () => {
    expect(permissionSource).toContain('IMPORT_PERMISSION_CREATE = "fair_crm.imports.create"');
    expect(source).toContain("const canCreate = can(IMPORT_PERMISSION_CREATE)");
  });

  it("fails closed for new uploads", () => {
    expect(source).toContain("const handleUpload = async () => {\n    if (!canCreate) return;");
    expect(source).toContain('currentStep === "upload" && !isSetupResume && !canCreate');
    expect(source).toContain('disabled={!canCreate}');
  });
});
