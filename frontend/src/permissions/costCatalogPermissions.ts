import { getGrantedCorePermissions } from "./corePermissions";

export const COST_CATEGORY_VIEW = "fair_crm.cost_catalog.categories.read";
export const COST_CATEGORY_CREATE = "fair_crm.cost_catalog.categories.create";
export const COST_CATEGORY_UPDATE = "fair_crm.cost_catalog.categories.update";
export const COST_CATEGORY_DELETE = "fair_crm.cost_catalog.categories.delete";
export const COST_PRODUCT_VIEW = "fair_crm.cost_catalog.products.read";
export const COST_PRODUCT_CREATE = "fair_crm.cost_catalog.products.create";
export const COST_PRODUCT_UPDATE = "fair_crm.cost_catalog.products.update";
export const COST_PRODUCT_DELETE = "fair_crm.cost_catalog.products.delete";

export function getGrantedCostCatalogPermissions(): Set<string> { return getGrantedCorePermissions(); }
export function canViewCostCatalog(): boolean {
  const granted = getGrantedCostCatalogPermissions();
  return granted.has(COST_CATEGORY_VIEW) || granted.has(COST_PRODUCT_VIEW);
}
