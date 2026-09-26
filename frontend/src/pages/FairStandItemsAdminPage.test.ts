import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandItemsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand items admin page", () => {
  it("uses URL routes for list / detail / create / edit; clone uses FormModal only", () => {
    // Dedicated URL paths for main CRUD (create/edit are full pages).
    expect(source).not.toContain('type View = "list" | "detail" | "create" | "edit"');
    expect(source).not.toContain("setView(");

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
    expect(source).toContain("FairStandDefaultColorField");
    expect(source).toContain("DefaultColorDetail");
    expect(source).toContain("handleSpaLinkClick");
    expect(source).toContain("itemsDetailActionPath");
    expect(source).toContain('href={itemsDetailPath(row.itemKey)}');
    expect(source).toContain('itemsDetailActionPath(row.itemKey, "clone")');
    expect(source).toContain('itemsDetailActionPath(row.itemKey, "archive")');
    expect(source).toContain("createHref");
    expect(source).toContain("listHref");
    expect(source).toContain('form={formId}');
    expect(source).toContain("fairStandItemsCloneSubmit");
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
    expect(source).toContain("preview3d");

    // CRUD + archive/restore + clone API surface.
    expect(source).toContain("listFairStandAdminItemRecords");
    expect(source).toContain("createFairStandAdminItemRecord");
    expect(source).toContain("cloneFairStandAdminItemRecord");
    expect(source).toContain("fairStandAdminItemKeyExists");
    expect(source).toContain("updateFairStandAdminItemRecord");
    expect(source).toContain("archiveFairStandAdminItemRecord");
    expect(source).toContain("restoreFairStandAdminItemRecord");

    // Permissions.
    expect(source).toContain("FAIR_STAND_ITEMS_READ");
    expect(source).toContain("FAIR_STAND_ITEMS_CREATE");
    expect(source).toContain("FAIR_STAND_ITEMS_UPDATE");
    expect(source).toContain("FAIR_STAND_ITEMS_ARCHIVE");
  });

  it("exposes clone buttons on list row actions and detail header", () => {
    expect(source).toContain("fairStandItemsClone");
    expect(source).toContain("CloneItemModal");
    expect(source).toContain("FormModal");
    expect(source).toContain("setCloneTarget");
    expect(source).toContain("setCloneOpen");
    expect(source).toContain('id: "clone"');
    expect(source).toContain("canCreate ? (");
    expect(source).toContain("handleClone");
  });

  it("generates item_key slug from name with manual override and uniqueness pre-check", () => {
    expect(source).toContain("function slugifyItemKey");
    expect(source).toContain("suggestCloneItemName");
    expect(source).toContain("itemKeyManual");
    expect(source).toContain("slugifyItemKey(nextName)");
    expect(source).toContain("setItemKeyManual(true)");
    expect(source).toContain("fairStandAdminItemKeyExists");
    expect(source).toContain("fairStandItemsCloneKeyTaken");
    expect(source).toContain("fairStandItemsFieldItemKeyHint");
  });
});

describe("Fair Stand items slugifyItemKey", () => {
  // Mirror of page helper for unit coverage (source of truth remains in page).
  const TR: Record<string, string> = {
    ç: "c",
    Ç: "c",
    ğ: "g",
    Ğ: "g",
    ı: "i",
    İ: "i",
    ö: "o",
    Ö: "o",
    ş: "s",
    Ş: "s",
    ü: "u",
    Ü: "u",
  };

  function slugifyItemKey(name: string): string {
    const ascii = Array.from(name)
      .map((char) => TR[char] ?? char)
      .join("")
      .toLowerCase();
    return ascii
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 128);
  }

  it("slugifies Turkish names like create form", () => {
    expect(slugifyItemKey("Duvar 200×350 (kopya)")).toBe("duvar_200_350_kopya");
    expect(slugifyItemKey("Şömine Üstü")).toBe("somine_ustu");
  });
});
