import { apiRequest } from "./client";
import type { CostCategory, CostCategoryOption, CostCategoryPayload, CostProduct, CostProductPayload } from "../types/costCatalog";

const base = "/api/v1/cost-catalog";

export const listCostCategories = () => apiRequest<{ items: CostCategory[] }>(`${base}/categories`);
export const createCostCategory = (payload: CostCategoryPayload) => apiRequest<CostCategory>(`${base}/categories`, { method: "POST", body: JSON.stringify(payload) });
export const updateCostCategory = (id: string, payload: CostCategoryPayload) => apiRequest<CostCategory>(`${base}/categories/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteCostCategory = (id: string) => apiRequest<void>(`${base}/categories/${encodeURIComponent(id)}`, { method: "DELETE" });

export const listCostProductCategoryOptions = () => apiRequest<{ items: CostCategoryOption[] }>(`${base}/products/category-options`);
export const listCostProducts = () => apiRequest<{ items: CostProduct[] }>(`${base}/products`);
export const createCostProduct = (payload: CostProductPayload) => apiRequest<CostProduct>(`${base}/products`, { method: "POST", body: JSON.stringify(payload) });
export const updateCostProduct = (id: string, payload: CostProductPayload) => apiRequest<CostProduct>(`${base}/products/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteCostProduct = (id: string) => apiRequest<void>(`${base}/products/${encodeURIComponent(id)}`, { method: "DELETE" });
