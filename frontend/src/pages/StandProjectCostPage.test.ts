import { describe, expect, it } from "vitest";
import { standProjectCostLabels } from "../labels/standProjectsLabels";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

describe("StandProjectCostPage", () => {
  it("loads the current project through the canonical BOM and shows calculation states", () => {
    const page = readFileSync(join(here, "StandProjectCostPage.tsx"), "utf8");
    const loader = readFileSync(join(here, "../domain/loadStandProjectCost.ts"), "utf8");
    expect(page).toContain("PERMISSION_STAND_PROJECTS_READ");
    expect(page).toContain("PERMISSION_COST_ITEMS_READ");
    expect(page).toContain("standProjectCostLabels.denied");
    expect(page).toContain("standProjectCostLabels.loading");
    expect(page).toContain("standProjectCostLabels.emptyTitle");
    expect(page).toContain("standProjectCostLabels.loadError");
    expect(page).toContain("standProjectCostLabels.missingPrice");
    expect(page).toContain("Badge variant=\"neutral\"");
    expect(page).toContain("standProjectCostLabels.filterSearch");
    expect(page).toContain("stand-project-cost-toolbar");
    expect(page).toContain("sortCostSheetRows");
    expect(page).toContain("onSortChange={changeSort}");
    expect(page).toContain("stand-project-cost-total-band");
    expect(page).toContain("standProjectCostLabels.bandBomPurchase");
    expect(page).toContain("standProjectCostLabels.bandManualSale");
    expect(page).toContain("standProjectCostLabels.bandGrandSale");
    expect(page).toContain("sheet.totals.grandPurchase");
    expect(page).toContain("sheet.totals.grandSale");
    expect(page).toContain("standProjectCostLabels.missingPriceNotice");
    expect(page).toContain("loadStandProjectCost");
    expect(page).not.toContain("organizationId");
    expect(loader).toContain("getFairStandProject");
    expect(loader).toContain("listFairStandCostItems");
    expect(loader).toContain("resolveProjectBom");
    const fallback = (file: string) => readFileSync(join(here, "../fairStand", file), "utf8");
    expect(fallback("catalog.js")).toContain("export function initializeCatalogCategories");
    expect(fallback("catalog.js")).toContain("export function initializeCatalogPreviews");
    expect(fallback("runtimeSettings.js")).toContain("export function initializeRuntimeSettings");
    expect(fallback("standDimensions.js")).toContain("export function initializeStandDimensions");
    expect(fallback("items.js")).toContain("export function initializeItemRegistry");
    expect(fallback("items.js")).toContain("export function initializeSnapRuleRegistry");
    expect(fallback("items.js")).toContain("export function initializeItemTypeRegistry");
    expect(fallback("projectBom.js")).toContain("export function resolveProjectBom");
    expect(loader).toContain('"/api/v1/fair-stand/catalog/bootstrap"');
    expect(loader).not.toContain("organizationId:");
  });

  it("shows Sahne Elemanı for BOM rows and keeps the source code BOM", () => {
    expect(standProjectCostLabels.sourceBom).toBe("Sahne Elemanı");
    expect(standProjectCostLabels.sourceManual).toBe("Manuel");
    expect(standProjectCostLabels.bandBomPurchase).toBe("Sahne Elemanı Alış Tplm.");
    expect(standProjectCostLabels.bandBomSale).toBe("Sahne Elemanı Satış Tplm.");
    const sheet = readFileSync(join(here, "../domain/standProjectCost.ts"), "utf8");
    expect(sheet).toContain('source: "BOM"');
    const page = readFileSync(join(here, "StandProjectCostPage.tsx"), "utf8");
    expect(page).toContain('row.source === "BOM"');
  });
});
