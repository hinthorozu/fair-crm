import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { calculationUnitLabel } from "../api/fairStandCostItems";
import { costItemFormError, costItemFormFields, costItemOptionsForForm } from "./StandCostItemsPage";
import { costItemsLabels } from "../labels/costItemsLabels";
import { uiLabels } from "../labels/uiLabels";

const here = dirname(fileURLToPath(import.meta.url));

describe("StandCostItemsPage", () => {
  it("names the screen and menu Maliyet Kalemleri", () => {
    expect(costItemsLabels.pageTitle).toBe("Maliyet Kalemleri");
    expect(uiLabels.navStandCostItems).toBe("Maliyet Kalemleri");
  });

  it("shows create, edit and delete only behind their permissions", () => {
    const source = readFileSync(join(here, "StandCostItemsPage.tsx"), "utf8");
    expect(source).toContain("PERMISSION_COST_ITEMS_READ");
    expect(source).toContain("PERMISSION_COST_ITEMS_CREATE");
    expect(source).toContain("PERMISSION_COST_ITEMS_UPDATE");
    expect(source).toContain("PERMISSION_COST_ITEMS_DELETE");
    expect(source).toContain("listFairStandCostItemFormCatalog");
    const client = readFileSync(join(here, "../api/fairStandCostItems.ts"), "utf8");
    expect(client).toContain("/api/v1/fair-stand/cost-items");
    expect(client).toContain("/api/v1/fair-stand/catalog/bootstrap");
    expect(client).toContain("isCostEnabled === true");
    expect(source).toContain("canCreate");
    expect(source).toContain("canUpdate");
    expect(source).toContain("canDelete");
    expect(source).toContain("if (!canRead)");
  });

  it("hides an item that already has a price from the create dropdown", () => {
    const options = [
      { itemKey: "askilik", name: "Askılık", unitName: "Adet" },
      { itemKey: "kettle", name: "Kettle", unitName: "Adet" },
    ];
    expect(costItemOptionsForForm(options, ["askilik"], null)).toEqual([
      { itemKey: "kettle", name: "Kettle", unitName: "Adet" },
    ]);
    expect(costItemOptionsForForm(options, ["askilik"], "askilik")).toEqual([
      { itemKey: "askilik", name: "Askılık", unitName: "Adet" },
    ]);
  });

  it("shows the catalog unit name on the row and does not store it on the price", () => {
    expect(calculationUnitLabel("adet", [{ unitKey: "adet", name: "Adet" }])).toBe("Adet");
    expect(calculationUnitLabel("metre_kare", [{ unitKey: "metre_kare", name: "Metre Kare" }])).toBe("Metre Kare");
    expect(calculationUnitLabel(null, [])).toBe("");
    const source = readFileSync(join(here, "StandCostItemsPage.tsx"), "utf8");
    expect(source).toContain("colUnit");
    expect(source).toContain("unitNames");
    const client = readFileSync(join(here, "../api/fairStandCostItems.ts"), "utf8");
    expect(client).toContain("calculationUnitLabel(item.unit, units)");
    expect(client).toContain("purchasePrice: string");
    expect(client).toContain("unit: string | null");
    expect(source).toContain("costItemType === \"MANUAL\"");
    expect(source).toContain("calculationUnitLabel(row.unit, units)");
  });

  it("shows item fields or manual name and unit catalog fields", () => {
    expect(costItemFormFields("ITEM")).toEqual({ item: true, name: false, unit: false });
    expect(costItemFormFields("MANUAL")).toEqual({ item: false, name: true, unit: true });
    expect(costItemsLabels.typeItem).toBe("Item");
    expect(costItemsLabels.typeManual).toBe("Manuel");
    expect(costItemsLabels.colType).toBe("Tür");
    const source = readFileSync(join(here, "StandCostItemsPage.tsx"), "utf8");
    expect(source).toContain("cost-item-type");
    expect(source).toContain("cost-item-name");
    expect(source).toContain("cost-item-unit");
    expect(costItemFormError("10", "", { type: "MANUAL", name: "", unitKey: "adet" })).toBe("Kalem adı boş bırakılamaz.");
    expect(costItemFormError("10", "", { type: "MANUAL", name: "Nakliye", unitKey: "" })).toBe("Birim seçilmelidir.");
    expect(costItemFormError("10", "", { type: "MANUAL", name: "Nakliye", unitKey: "adet" })).toBeNull();
  });

  it("requires a non-negative purchase price and allows an empty sale price", () => {
    expect(costItemFormError("", "")).toBe("Alış fiyatı boş bırakılamaz.");
    expect(costItemFormError("-1", "")).toBe("Alış fiyatı 0 veya daha büyük olmalı.");
    expect(costItemFormError("0", "")).toBeNull();
    expect(costItemFormError("10", "")).toBeNull();
    expect(costItemFormError("10", "0")).toBeNull();
    expect(costItemFormError("10", "-2")).toBe("Satış fiyatı 0 veya daha büyük olmalı.");
  });
});
