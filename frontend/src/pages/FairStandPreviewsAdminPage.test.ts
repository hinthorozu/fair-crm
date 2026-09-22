import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandPreviewsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand previews admin page", () => {
  it("uses shared PageShell/table/form standards", () => {
    expect(source).toContain("PageShell");
    expect(source).toContain("PageHeader");
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("FormModal");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain("FormField");
    expect(source).toContain("Badge");
    expect(source).toContain("ConfirmDialog");
    expect(source).toContain('formWidth="wide"');
  });

  it("keeps the live catalog preview and its form sections", () => {
    expect(source).toContain("FairStandCatalogLivePreview");
    expect(source).toContain("adminLabels.fairStandPreviewsSectionIdentity");
    expect(source).toContain("adminLabels.fairStandPreviewsSectionMarkup");
    expect(source).toContain("adminLabels.fairStandPreviewsSectionLivePreview");
  });

  it("uses adminLabels copy and field hints", () => {
    expect(source).toContain("adminLabels.fairStandPreviewsTitle");
    expect(source).toContain("adminLabels.fairStandPreviewsFieldNameHint");
    expect(source).toContain("adminLabels.fairStandPreviewsFieldIndexHint");
    expect(source).toContain("adminLabels.fairStandPreviewsFieldActiveHint");
    expect(source).toContain("adminLabels.fairStandPreviewsFieldMarkupHint");
    expect(source).toContain("adminLabels.fairStandPreviewsFieldCssHint");
    expect(source).not.toContain("Katalog Önizlemeleri\"");
  });

  it("uses UniversalDataTable column title, not deprecated header", () => {
    expect(source).toContain("title: adminLabels.fairStandPreviewsColActions");
    expect(source).toContain("sortable: false");
    expect(source).not.toMatch(/\bheader:/);
  });

  it("uses boolean CheckboxField onChange, not event.target.checked", () => {
    expect(source).toContain("onChange={(checked: boolean) =>");
    expect(source).not.toContain("event.target.checked");
  });
});
