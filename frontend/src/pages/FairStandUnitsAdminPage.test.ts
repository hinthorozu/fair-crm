import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandUnitsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand units admin page", () => {
  it("uses the shared admin page, table, and form standards", () => {
    expect(source).toContain("PageShell");
    expect(source).toContain("PageHeader");
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("FormModal");
    expect(source).toContain("ConfirmDialog");
    expect(source).toContain("Badge");
    expect(source).toContain('formWidth="narrow"');
  });

  it("lists code, name, symbol, and status and keeps inactive rows", () => {
    expect(source).toContain("adminLabels.fairStandUnitsColUnitKey");
    expect(source).toContain("adminLabels.fairStandUnitsColName");
    expect(source).toContain("adminLabels.fairStandUnitsColSymbol");
    expect(source).toContain("adminLabels.fairStandCatalogColStatus");
    expect(source).toContain("items={rows}");
    expect(source).toContain("row.isActive");
    expect(source).not.toContain(".filter((row) => row.isActive)");
  });

  it("creates, edits, archives, and restores through the catalog admin API", () => {
    expect(source).toContain("createFairStandAdminUnit");
    expect(source).toContain("updateFairStandAdminUnit");
    expect(source).toContain("archiveFairStandAdminUnit");
    expect(source).toContain("restoreFairStandAdminUnit");
    expect(source).toContain("adminLabels.fairStandCatalogActionArchive");
    expect(source).toContain("adminLabels.fairStandCatalogActionRestore");
    expect(source).toContain("setSaving(true)");
    expect(source).toContain("disabled={saving}");
    expect(source).toContain("unitKeyFromName(form.name)");
    expect(source).toContain("disabled readOnly");
    expect(source).toContain("adminLabels.fairStandUnitsFieldUnitKey");
    expect(source).toContain("row.unitKey");
    expect(source).not.toContain("row.code");
    expect(source).not.toContain("fairStandUnitsColCode");
    expect(source).not.toContain(".delete(");
  });

  it("gates the screen with catalog permissions, not a role string", () => {
    expect(source).toContain("getGrantedFairStandAdminPermissions");
    expect(source).toContain("FAIR_STAND_CATALOG_READ");
    expect(source).toContain("adminLabels.fairStandUnitsPermissionDenied");
    expect(source).not.toContain("super_admin");
    expect(source).not.toContain("role ===");
  });
});
