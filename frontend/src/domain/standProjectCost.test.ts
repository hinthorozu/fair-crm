import { describe, expect, it } from "vitest";
import type { FairStandCostItem } from "../api/fairStandCostItems";
import {
  buildStandProjectCostSheet,
  formatCostMoney,
  manualCostItemChoices,
  removeManualCostItem,
  selectManualCostItem,
  sortCostSheetRows,
} from "./standProjectCost";

const units = [
  { unitKey: "metre_kare", name: "Metre Kare" },
  { unitKey: "adet", name: "Adet" },
  { unitKey: "sefer", name: "Sefer" },
  { unitKey: "gun", name: "Gün" },
];

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

function manual(id: string, name: string, unit: string, purchase: string, sale: string): FairStandCostItem {
  return {
    id,
    organizationId: "org-a",
    costItemType: "MANUAL",
    itemKey: null,
    name,
    unit,
    purchasePrice: purchase,
    salePrice: sale,
    createdAt: 1,
    updatedAt: 1,
  };
}

const bomLines = [
  { itemKey: "digital_print", name: "Dijital Baskı", quantity: 12.5, unit: "metre_kare" },
  { itemKey: "elektrik_panosu", name: "Elektrik Panosu", quantity: 1, unit: "adet" },
  { itemKey: "carpet", name: "Halı", quantity: 30, unit: "metre_kare" },
];

describe("stand project cost sheet", () => {
  const prices = [
    itemPrice("digital_print", "200.00", "300.00"),
    itemPrice("carpet", "250.00", "350.00"),
    itemPrice("zero_sale", "10.00", "0.00"),
    manual("nakliye", "Nakliye", "sefer", "5000.00", "6000.00"),
    manual("iscilik", "İşçilik", "gun", "2500.00", "3000.00"),
  ];

  it("lists every BOM line, prices matches, and keeps an unpriced line out of the totals", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines,
      costItems: prices,
      manualEntries: [],
      units,
    });
    expect(sheet.rows.map((row) => row.name)).toEqual(["Dijital Baskı", "Halı", "Elektrik Panosu"]);
    const print = sheet.rows[0];
    expect(print.unitLabel).toBe("Metre Kare");
    expect(print.purchaseUnit).toBe(200);
    expect(print.saleUnit).toBe(300);
    expect(print.purchaseTotal).toBe(2500);
    expect(print.saleTotal).toBe(3750);
    expect(sheet.rows[1].purchaseTotal).toBe(7500);
    expect(sheet.rows[1].saleTotal).toBe(10500);
    expect(sheet.rows[2].purchaseUnit).toBeNull();
    expect(sheet.rows[2].saleUnit).toBeNull();
    expect(sheet.totals.unpricedBomCount).toBe(1);
    expect(sheet.totals.bomPurchase).toBe(10000);
    expect(sheet.totals.bomSale).toBe(14250);
    expect(formatCostMoney(sheet.totals.bomPurchase)).toBe("10.000,00");
  });

  it("puts a row with only a purchase or only a sale price ahead of rows with neither", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines: [
        { itemKey: "elektrik_panosu", name: "Elektrik Panosu", quantity: 1, unit: "adet" },
        { itemKey: "sale_only", name: "Yalnız Satış", quantity: 2, unit: "adet" },
        { itemKey: "purchase_only", name: "Yalnız Alış", quantity: 3, unit: "adet" },
      ],
      costItems: [
        itemPrice("sale_only", "", "40.00"),
        itemPrice("purchase_only", "15.00", ""),
      ],
      manualEntries: [],
      units,
    });
    expect(sheet.rows.map((row) => row.name)).toEqual(["Yalnız Satış", "Yalnız Alış", "Elektrik Panosu"]);
    expect(sheet.rows[0].purchaseUnit).toBeNull();
    expect(sheet.rows[0].saleTotal).toBe(80);
    expect(sheet.rows[1].saleUnit).toBeNull();
    expect(sheet.rows[1].purchaseTotal).toBe(45);
    expect(sheet.totals.unpricedBomCount).toBe(1);
    expect(sheet.totals.bomPurchase).toBe(45);
    expect(sheet.totals.bomSale).toBe(80);
  });

  it("treats a stored sale price of zero as a real price", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines: [{ itemKey: "zero_sale", name: "Sıfır Satış", quantity: 2, unit: "adet" }],
      costItems: prices,
      manualEntries: [],
      units,
    });
    expect(sheet.rows[0].saleUnit).toBe(0);
    expect(sheet.rows[0].saleTotal).toBe(0);
    expect(sheet.totals.unpricedBomCount).toBe(0);
    expect(sheet.totals.bomSale).toBe(0);
    expect(sheet.totals.bomPurchase).toBe(20);
  });

  it("adds one manual row, recalculates quantity, and does not duplicate the same item", () => {
    expect(manualCostItemChoices(prices).map((item) => item.name)).toEqual(["Nakliye", "İşçilik"]);
    const once = selectManualCostItem([], "nakliye");
    const again = selectManualCostItem(once, "nakliye");
    expect(again).toEqual([{ costItemId: "nakliye", quantity: "2" }]);
    const withLabor = selectManualCostItem(again, "iscilik");
    const laborThree = withLabor.map((entry) =>
      entry.costItemId === "iscilik" ? { ...entry, quantity: "3" } : entry,
    );
    const sheet = buildStandProjectCostSheet({
      bomLines,
      costItems: prices,
      manualEntries: laborThree,
      units,
    });
    expect(sheet.rows.slice(0, 2).map((row) => row.name)).toEqual(["Nakliye", "İşçilik"]);
    const manualRows = sheet.rows.filter((row) => row.source === "MANUAL");
    expect(manualRows.map((row) => row.name)).toEqual(["Nakliye", "İşçilik"]);
    expect(manualRows[0].unitLabel).toBe("Sefer");
    expect(manualRows[0].purchaseTotal).toBe(10000);
    expect(manualRows[0].saleTotal).toBe(12000);
    expect(manualRows[1].quantity).toBe(3);
    expect(manualRows[1].purchaseTotal).toBe(7500);
    expect(sheet.totals.manualPurchase).toBe(17500);
    expect(sheet.totals.manualSale).toBe(21000);
    expect(sheet.totals.grandPurchase).toBe(27500);
    expect(sheet.totals.grandSale).toBe(35250);
    const changed = buildStandProjectCostSheet({
      bomLines,
      costItems: prices,
      manualEntries: laborThree.map((entry) =>
        entry.costItemId === "nakliye" ? { ...entry, quantity: "4" } : entry,
      ),
      units,
    });
    expect(changed.rows.find((row) => row.name === "Nakliye")?.purchaseTotal).toBe(20000);
    expect(removeManualCostItem(laborThree, "nakliye").map((entry) => entry.costItemId)).toEqual(["iscilik"]);
  });

  it("ignores a manual cost item that is not in the supplied organization list", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines: [],
      costItems: prices,
      manualEntries: [{ costItemId: "other-org-manual", quantity: "2" }],
      units,
    });
    expect(sheet.rows).toEqual([]);
    expect(sheet.totals.grandPurchase).toBe(0);
  });

  it("sorts the loaded rows by a column without calling the backend", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines,
      costItems: prices,
      manualEntries: [],
      units,
    });
    expect(sortCostSheetRows(sheet.rows, "name", "asc").map((row) => row.name)).toEqual([
      "Dijital Baskı",
      "Elektrik Panosu",
      "Halı",
    ]);
    expect(sortCostSheetRows(sheet.rows, "name", "desc").map((row) => row.name)).toEqual([
      "Halı",
      "Elektrik Panosu",
      "Dijital Baskı",
    ]);
    expect(sortCostSheetRows(sheet.rows, "purchaseUnit", "asc").map((row) => row.name)).toEqual([
      "Dijital Baskı",
      "Halı",
      "Elektrik Panosu",
    ]);
    expect(sortCostSheetRows(sheet.rows, "purchaseUnit", "desc").map((row) => row.name)).toEqual([
      "Halı",
      "Dijital Baskı",
      "Elektrik Panosu",
    ]);
    expect(sortCostSheetRows(sheet.rows, "quantity", "asc").map((row) => row.quantity)).toEqual([1, 12.5, 30]);
  });

  it("keeps a decimal manual quantity", () => {
    const sheet = buildStandProjectCostSheet({
      bomLines: [],
      costItems: prices,
      manualEntries: [{ costItemId: "nakliye", quantity: "1,5" }],
      units,
    });
    expect(sheet.rows[0].quantity).toBe(1.5);
    expect(sheet.rows[0].purchaseTotal).toBe(7500);
  });
});
