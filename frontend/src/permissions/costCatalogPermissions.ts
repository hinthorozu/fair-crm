import { getGrantedCorePermissions } from "./corePermissions";

export const COST_CATEGORY_VIEW = "cost_catalog.category.view";
export const COST_CATEGORY_CREATE = "cost_catalog.category.create";
export const COST_CATEGORY_UPDATE = "cost_catalog.category.update";
export const COST_CATEGORY_DELETE = "cost_catalog.category.delete";
export const COST_PRODUCT_VIEW = "cost_catalog.product.view";
export const COST_PRODUCT_CREATE = "cost_catalog.product.create";
export const COST_PRODUCT_UPDATE = "cost_catalog.product.update";
export const COST_PRODUCT_DELETE = "cost_catalog.product.delete";

export function getGrantedCostCatalogPermissions(): Set<string> { return getGrantedCorePermissions(); }
export function canViewCostCatalog(): boolean {
  const granted = getGrantedCostCatalogPermissions();
  return granted.has(COST_CATEGORY_VIEW) || granted.has(COST_PRODUCT_VIEW);
}
