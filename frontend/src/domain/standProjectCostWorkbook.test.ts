import { describe, expect, it } from "vitest";
import JSZip from "jszip";
import type { FairStandCostItem } from "../api/fairStandCostItems";
import { standProjectCostLabels } from "../labels/standProjectsLabels";
import { buildStandProjectCostSheet } from "./standProjectCost";
import {
  buildStandProjectCostWorkbook,
  costSheetExportRows,
  costWorkbookFileName,
} from "./standProjectCostWorkbook";

function itemPrice(itemKey: string, purchase: string, sale: string): FairStandCostItem {
  return {
    id: `item-${itemKey}`,
    organizationId: "org-a",
    costItemType: "ITEM",
    itemKey,
    name: null,
    unit: null,
    purchasePrice: purchase,
    salePrice: sale,
    createdAt: 1,
    updatedAt: 1,
  };
}

describe("stand project cost workbook", () => {
  const units = [
    { unitKey: "metre_kare", name: "Metre Kare" },
    { unitKey: "adet", name: "Adet" },
  ];

  it("writes the rows it is given, in that order, then the six on-screen totals", async () => {
    const sheet = buildStandProjectCostSheet({
      bomLines: [
        { itemKey: "digital_print", name: "Dijital Baskı", quantity: 12.5, unit: "metre_kare" },
        { itemKey: "elektrik_panosu", name: "Elektrik Panosu", quantity: 1, unit: "adet" },
      ],
      costItems: [itemPrice("digital_print", "200.00", "300.00")],
      manualEntries: [],
      units,
    });
    const visible = [sheet.rows[1], sheet.rows[0]];
    const cells = costSheetExportRows(visible, sheet.totals);

    expect(cells[0]).toEqual([
      standProjectCostLabels.colSource,
      standProjectCostLabels.colName,
      standProjectCostLabels.colQuantity,
      standProjectCostLabels.colUnit,
      standProjectCostLabels.colPurchaseUnit,
      standProjectCostLabels.colPurchaseTotal,
      standProjectCostLabels.colSaleUnit,
      standProjectCostLabels.colSaleTotal,
    ]);
    expect(cells[1]).toEqual([
      "Sahne Elemanı",
      "Elektrik Panosu",
      1,
      "Adet",
      standProjectCostLabels.missingPrice,
      standProjectCostLabels.noTotal,
      standProjectCostLabels.missingPrice,
      standProjectCostLabels.noTotal,
    ]);
    expect(cells[2]).toEqual(["Sahne Elemanı", "Dijital Baskı", 12.5, "Metre Kare", 200, 2500, 300, 3750]);
    expect(cells[3]).toEqual([]);
    expect(cells.slice(4)).toEqual([
      [standProjectCostLabels.bandBomPurchase, sheet.totals.bomPurchase],
      [standProjectCostLabels.bandBomSale, sheet.totals.bomSale],
      [standProjectCostLabels.bandManualPurchase, sheet.totals.manualPurchase],
      [standProjectCostLabels.bandManualSale, sheet.totals.manualSale],
      [standProjectCostLabels.bandGrandPurchase, sheet.totals.grandPurchase],
      [standProjectCostLabels.bandGrandSale, sheet.totals.grandSale],
    ]);
    expect(sheet.totals.bomPurchase).toBe(2500);
    expect(sheet.totals.grandSale).toBe(3750);

    const blob = await buildStandProjectCostWorkbook(visible, sheet.totals);
    const zip = await JSZip.loadAsync(await blob.arrayBuffer());
    const workbook = await zip.file("xl/workbook.xml")?.async("string");
    const worksheet = await zip.file("xl/worksheets/sheet1.xml")?.async("string");
    expect(workbook).toContain('name="Maliyet"');
    expect(worksheet).toContain("Elektrik Panosu");
    expect(worksheet).toContain("<v>2500</v>");
    expect(worksheet).toContain(standProjectCostLabels.bandGrandSale);
    expect(worksheet?.indexOf("Elektrik Panosu")).toBeLessThan(worksheet?.indexOf("Dijital Baskı") ?? 0);
  });

  it("builds a file name from the project name", () => {
    expect(costWorkbookFileName("  Proje Adı  ")).toBe("Proje Adı - maliyet.xlsx");
    expect(costWorkbookFileName('A/B:C*')).toBe("A B C - maliyet.xlsx");
    expect(costWorkbookFileName("   ")).toBe("maliyet - maliyet.xlsx");
  });
});
