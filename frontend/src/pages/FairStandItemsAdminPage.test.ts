import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandItemsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand items admin page", () => {
  it("uses Fair Stand admin table + modal standards with full item CRUD and satellites", () => {
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("FormModal");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain('formWidth="wide"');
    expect(source).toContain("adminLabels.fairStandItemsTitle");
    expect(source).toContain("listFairStandAdminItemRecords");
    expect(source).toContain("getFairStandAdminItemRecord");
    expect(source).toContain("createFairStandAdminItemRecord");
    expect(source).toContain("updateFairStandAdminItemRecord");
    expect(source).toContain("archiveFairStandAdminItemRecord");
    expect(source).toContain("restoreFairStandAdminItemRecord");
    expect(source).toContain("fairStandItemsFieldItemKeyHint");
    expect(source).toContain("fairStandItemsFieldCatalogVisibleHint");
    expect(source).toContain("fairStandItemsFieldStripCountHint");
    expect(source).toContain("fairStandItemsSectionComponents");
    expect(source).toContain("fairStandItemsSectionAssets");
    expect(source).toContain("fairStandItemsSectionBodyParts");
    expect(source).toContain("fairStandItemsSectionVideoWall");
    expect(source).toContain("FAIR_STAND_ITEMS_READ");
    expect(source).toContain("FAIR_STAND_ITEMS_CREATE");
    expect(source).toContain("FAIR_STAND_ITEMS_UPDATE");
    expect(source).toContain("FAIR_STAND_ITEMS_ARCHIVE");
  });
});
