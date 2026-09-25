import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandItemsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand items admin page", () => {
  it("uses URL routes for list / detail / create / edit without FormModal or viewstate", () => {
    // No popup/modal for create or edit.
    expect(source).not.toContain("FormModal");
    expect(source).not.toContain('type View = "list" | "detail" | "create" | "edit"');
    expect(source).not.toContain("setView(");

    // Dedicated URL paths.
    expect(source).toContain('ITEMS_BASE_PATH = "/admin/fair-stand/items"');
    expect(source).toContain("itemsCreatePath");
    expect(source).toContain("itemsDetailPath");
    expect(source).toContain("itemsEditPath");
    expect(source).toContain("parseItemsRoute");
    expect(source).toContain("${ITEMS_BASE_PATH}/new");
    expect(source).toContain("/edit");

    // List + detail (önizleme) flow.
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("FilterPanel");
    expect(source).toContain("useServerDataTable");
    expect(source).toContain("table={table}");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("fairStandItemsActionView");
    expect(source).toContain("getFairStandAdminItemRecord");
    expect(source).toContain("fairStandItemsFilterSearch");
    expect(source).toContain("fairStandItemsRefresh");
    expect(source).toContain('className="btn link"');
    expect(source).toContain("btn link danger");
    expect(source).toContain("<Badge");
    expect(source).toContain('variant={row.catalogVisible ? "success" : "neutral"}');

    // Full-page forms use FormActions + crm-form--wide, no modal.
    expect(source).toContain("FormActions");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain("FormDirtyHost");
    expect(source).toContain("crm-form crm-form--wide");
    expect(source).toContain("crm-form--narrow");

    // Alt items rendered as tables (components / body parts / assets).
    expect(source).toContain("componentColumns");
    expect(source).toContain("fairStandItemsComponentsDescription");
    expect(source).toContain("fairStandItemsBodyPartsDescription");
    expect(source).toContain("fairStandItemsAssetsDescription");
    expect(source).toContain("fairStandItemsEmptyComponents");

    expect(source).toContain("listFairStandAdminCategories");
    expect(source).toContain("listFairStandAdminPreviews");
    expect(source).toContain("FairStandCatalogPreviewSelect");
    expect(source).toContain("fairStandCatalogSelectPlaceholder");

    // Detail preview + shared hints.
    expect(source).toContain("Tabs");
    expect(source).toContain("TabPanel");
    expect(source).toContain("detail-grid");
    expect(source).toContain("fairStandItemsTabGeneral");
    expect(source).toContain("fairStandItemsFieldItemKeyHint");
    expect(source).toContain("fairStandItemsFieldCatalogVisibleHint");
    expect(source).toContain("fairStandItemsFieldStripCountHint");

    // Sections.
    expect(source).toContain("fairStandItemsSectionComponents");
    expect(source).toContain("fairStandItemsSectionAssets");
    expect(source).toContain("fairStandItemsSectionBodyParts");
    expect(source).toContain("fairStandItemsSectionVideoWall");

    expect(source).toContain("FairStandItem3dPreview");
    expect(source).toContain("fairStandItemsTabPreview3d");
    expect(source).toContain('preview3d');

    // CRUD + archive/restore API surface preserved.
    expect(source).toContain("listFairStandAdminItemRecords");
    expect(source).toContain("createFairStandAdminItemRecord");
    expect(source).toContain("updateFairStandAdminItemRecord");
    expect(source).toContain("archiveFairStandAdminItemRecord");
    expect(source).toContain("restoreFairStandAdminItemRecord");

    // Permissions.
    expect(source).toContain("FAIR_STAND_ITEMS_READ");
    expect(source).toContain("FAIR_STAND_ITEMS_CREATE");
    expect(source).toContain("FAIR_STAND_ITEMS_UPDATE");
    expect(source).toContain("FAIR_STAND_ITEMS_ARCHIVE");
  });
});
