import { apiRequest } from "../api/client";
import type { FairStandCostItem } from "../api/fairStandCostItems";
import { listFairStandCostItems } from "../api/fairStandCostItems";
import { getFairStandProject } from "../api/fairStandProjects";
import type { BomCostSourceLine } from "./standProjectCost";

type CatalogUnit = { unitKey?: string; name?: string };

type CatalogBootstrap = {
  items?: unknown[];
  categories?: unknown[];
  previewKinds?: unknown[];
  standDimensions?: unknown;
  settings?: unknown;
  rules?: unknown[];
  itemTypes?: unknown[];
  units?: CatalogUnit[];
};

export type LoadedStandProjectCost = {
  projectId: string;
  projectName: string;
  bomLines: BomCostSourceLine[];
  costItems: FairStandCostItem[];
  units: CatalogUnit[];
};

function assetNameMap(assets: Array<{ id?: string; name?: string }> | undefined): Record<string, string> {
  const names: Record<string, string> = {};
  for (const asset of assets ?? []) {
    if (typeof asset?.id === "string" && asset.id) names[asset.id] = asset.name ?? "";
  }
  return names;
}

async function installCatalog(payload: CatalogBootstrap): Promise<void> {
  if (
    !payload
    || !Array.isArray(payload.items)
    || !Array.isArray(payload.categories)
    || !Array.isArray(payload.previewKinds)
    || !payload.standDimensions
    || !payload.settings
  ) {
    throw new TypeError("Fair Stand Item catalog bootstrap payload is invalid.");
  }
  const catalog = await import("@fair-stand/catalog.js");
  const settings = await import("@fair-stand/runtimeSettings.js");
  const dimensions = await import("@fair-stand/standDimensions.js");
  const items = await import("@fair-stand/items.js");
  dimensions.initializeStandDimensions(payload.standDimensions);
  settings.initializeRuntimeSettings(payload.settings);
  catalog.initializeCatalogCategories(payload.categories);
  catalog.initializeCatalogPreviews(payload.previewKinds);
  items.initializeSnapRuleRegistry(Array.isArray(payload.rules) ? payload.rules : []);
  items.initializeItemTypeRegistry(Array.isArray(payload.itemTypes) ? payload.itemTypes : []);
  items.initializeItemRegistry(payload.items);
}

export async function loadStandProjectCost(projectId: string): Promise<LoadedStandProjectCost> {
  const [project, costItems, bootstrap] = await Promise.all([
    getFairStandProject(projectId),
    listFairStandCostItems(),
    apiRequest<CatalogBootstrap>("/api/v1/fair-stand/catalog/bootstrap"),
  ]);
  await installCatalog(bootstrap);
  const { resolveProjectBom } = await import("@fair-stand/projectBom.js");
  const bom = resolveProjectBom(
    Array.isArray(project.modules) ? project.modules : [],
    project.stand ?? null,
    assetNameMap(project.assets),
  );
  const bomLines: BomCostSourceLine[] = (Array.isArray(bom?.lines) ? bom.lines : []).map((line) => ({
    itemKey: String(line.itemKey),
    name: typeof line.name === "string" && line.name ? line.name : String(line.itemKey),
    quantity: Number(line.quantity),
    unit: String(line.unit ?? ""),
  }));
  return {
    projectId: project.id,
    projectName: project.name || "Adsız Proje",
    bomLines,
    costItems,
    units: Array.isArray(bootstrap.units) ? bootstrap.units : [],
  };
}
