import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandCatalogAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand catalog admin page", () => {
  it("uses shared PageShell/table/form standards", () => {
    expect(source).toContain("PageShell");
    expect(source).toContain("PageHeader");
    expect(source).toContain("SectionHeader");
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("FormModal");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain("FormField");
    expect(source).toContain("Badge");
    expect(source).toContain("ConfirmDialog");
    expect(source).toContain('formWidth="narrow"');
    expect(source).toContain('formWidth="standard"');
  });

  it("keeps both catalog sections", () => {
    expect(source).toContain("adminLabels.fairStandCatalogCategorySection");
    expect(source).toContain("adminLabels.fairStandCatalogItemSection");
    expect(source).toContain("adminLabels.fairStandCatalogCategoryModalSection");
    expect(source).toContain("adminLabels.fairStandCatalogItemModalSection");
  });

  it("exposes section titles and client search filters", () => {
    expect(source).toContain("SectionHeader");
    expect(source).toContain("FilterPanel");
    expect(source).toContain("fairStandCatalogCategoryFilterSearch");
    expect(source).toContain("fairStandCatalogItemFilterSearch");
    expect(source).toContain("filteredCategories");
    expect(source).toContain("filteredItems");
  });

  it("uses adminLabels copy and field hints", () => {
    expect(source).toContain("adminLabels.fairStandCatalogTitle");
    expect(source).toContain("adminLabels.fairStandCatalogFieldNameHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldIndexHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldActiveHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldItemVisibleHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldItemCategoryHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldItemIndexHint");
    expect(source).toContain("adminLabels.fairStandCatalogFieldItemPreviewHint");
    expect(source).not.toContain("Katalog Yönetimi\"");
  });

  it("uses visual catalog preview select in the item binding modal", () => {
    expect(source).toContain("FairStandCatalogPreviewSelect");
    expect(source).toContain("fairStandCatalogFieldItemPreview");
  });

  it("uses UniversalDataTable column title, not deprecated header", () => {
    expect(source).toContain("title: adminLabels.fairStandCatalogColActions");
    expect(source).toContain("sortable: false");
    expect(source).not.toMatch(/\bheader:/);
  });

  it("uses boolean CheckboxField onChange, not event.target.checked", () => {
    expect(source).toContain("onChange={(checked: boolean) =>");
    expect(source).not.toContain("event.target.checked");
  });
});
