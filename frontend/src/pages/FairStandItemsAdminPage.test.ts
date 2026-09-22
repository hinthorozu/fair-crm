import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandItemsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand items admin page", () => {
  it("uses list → detail (görüntüle) → full-page create/edit flow without FormModal", () => {
    // No popup/modal for create or edit.
    expect(source).not.toContain("FormModal");

    // List + detail (önizleme) view flow.
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("fairStandItemsActionView");
    expect(source).toContain("getFairStandAdminItemRecord");

    // Full-page forms use FormActions + crm-form--wide, no modal.
    expect(source).toContain("FormActions");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain("FormDirtyHost");
    expect(source).toContain('crm-form crm-form--wide');
    expect(source).toContain("crm-form--narrow");

    // Alt items rendered as tables (components / body parts / assets).
    expect(source).toContain("componentColumns");
    expect(source).toContain("fairStandItemsComponentsDescription");
    expect(source).toContain("fairStandItemsBodyPartsDescription");
    expect(source).toContain("fairStandItemsAssetsDescription");
    expect(source).toContain("fairStandItemsEmptyComponents");

    // Detail preview + shared hints.
    expect(source).toContain("DetailField");
    expect(source).toContain("field-hint");
    expect(source).toContain("fairStandItemsFieldItemKeyHint");
    expect(source).toContain("fairStandItemsFieldCatalogVisibleHint");
    expect(source).toContain("fairStandItemsFieldStripCountHint");

    // Sections.
    expect(source).toContain("fairStandItemsSectionComponents");
    expect(source).toContain("fairStandItemsSectionAssets");
    expect(source).toContain("fairStandItemsSectionBodyParts");
    expect(source).toContain("fairStandItemsSectionVideoWall");

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
