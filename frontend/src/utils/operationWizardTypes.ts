import type {
  OperationType,
  OperationTypeCatalogItem,
  OperationTypeMetadata,
} from "../types/operation";

/** Human todos belong under Görevler; keep them out of the automation type picker. */
export const WIZARD_EXCLUDED_TYPES: OperationType[] = ["manual_task"];

const PROMOTED_TYPES: OperationType[] = ["scraper", "bulk_email"];

/** Per-type wizard routes — no shared multi-type configuration wizard. */
export const OPERATION_TYPE_WIZARD_PATHS: Partial<Record<OperationType, string>> = {
  scraper: "/operations/new/scraper",
  bulk_email: "/operations/new/bulk-email",
};

export function getOperationTypeWizardPath(type: OperationType): string | null {
  return OPERATION_TYPE_WIZARD_PATHS[type] ?? null;
}

export function canContinueOperationType(
  type: OperationType | "",
  metaByType: Map<string, OperationTypeMetadata>,
): boolean {
  if (!type) return false;
  if (!getOperationTypeWizardPath(type)) return false;
  return metaByType.has(type);
}

export function buildCatalogNameMap(
  catalog: OperationTypeCatalogItem[],
): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of catalog) {
    map.set(item.key, item.name);
  }
  return map;
}

export function buildCatalogSortMap(
  catalog: OperationTypeCatalogItem[],
): Map<string, number> {
  const map = new Map<string, number>();
  for (const item of catalog) {
    map.set(item.key, item.sort_order);
  }
  return map;
}

/**
 * Wizard picker types = registry wizard metadata ∩ active DB catalog keys.
 * Display order prefers DB sort_order, then promoted types, then name.
 */
export function sortWizardTypes(
  types: OperationTypeMetadata[],
  catalog: OperationTypeCatalogItem[] = [],
): OperationTypeMetadata[] {
  const activeKeys = new Set(
    catalog.filter((item) => item.is_active).map((item) => item.key),
  );
  const sortMap = buildCatalogSortMap(catalog);
  const nameMap = buildCatalogNameMap(catalog);

  const available = types.filter((item) => {
    if (!item.available_in_wizard) return false;
    if (WIZARD_EXCLUDED_TYPES.includes(item.type as OperationType)) return false;
    if (activeKeys.size > 0 && !activeKeys.has(item.type)) return false;
    return true;
  });

  return [...available].sort((a, b) => {
    const aSort = sortMap.get(a.type);
    const bSort = sortMap.get(b.type);
    if (aSort != null && bSort != null && aSort !== bSort) return aSort - bSort;
    if (aSort != null && bSort == null) return -1;
    if (aSort == null && bSort != null) return 1;

    const aPromo = PROMOTED_TYPES.indexOf(a.type as OperationType);
    const bPromo = PROMOTED_TYPES.indexOf(b.type as OperationType);
    const aRank = aPromo === -1 ? PROMOTED_TYPES.length : aPromo;
    const bRank = bPromo === -1 ? PROMOTED_TYPES.length : bPromo;
    if (aRank !== bRank) return aRank - bRank;

    const aLabel = nameMap.get(a.type) ?? a.type;
    const bLabel = nameMap.get(b.type) ?? b.type;
    return aLabel.localeCompare(bLabel, "tr");
  });
}
