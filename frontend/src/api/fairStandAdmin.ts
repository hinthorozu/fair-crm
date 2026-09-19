import { apiRequest } from "./client";

const base = "/api/v1/fair-stand/admin";

export type FairStandAdminCategory = {
  id: number;
  catalogName: string;
  catalogIndex: number;
  isActive: boolean;
};

export type FairStandAdminItem = {
  itemKey: string;
  name: string;
  catalogVisible: boolean;
  categoryId: number | null;
  catalogItemIndex: number | null;
  previewId: number | null;
  isActive: boolean;
};

export type FairStandAdminPreview = {
  id: number;
  displayName: string;
  markup: string;
  cssCode: string;
  sortIndex: number;
  isActive: boolean;
};

export const listFairStandAdminCategories = () =>
  apiRequest<FairStandAdminCategory[]>(`${base}/categories`);
export const createFairStandAdminCategory = (payload: {
  catalog_name: string;
  catalog_index: number;
  is_active?: boolean;
}) => apiRequest<FairStandAdminCategory>(`${base}/categories`, { method: "POST", body: JSON.stringify(payload) });
export const updateFairStandAdminCategory = (
  categoryId: number,
  payload: { catalog_name?: string; catalog_index?: number; is_active?: boolean },
) =>
  apiRequest<FairStandAdminCategory>(`${base}/categories/${categoryId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminCategory = (categoryId: number) =>
  apiRequest<FairStandAdminCategory>(`${base}/categories/${categoryId}/archive`, {
    method: "POST",
  });
export const restoreFairStandAdminCategory = (categoryId: number) =>
  apiRequest<FairStandAdminCategory>(`${base}/categories/${categoryId}/restore`, {
    method: "POST",
  });

export const listFairStandAdminItems = () => apiRequest<FairStandAdminItem[]>(`${base}/items`);
export const updateFairStandAdminItem = (
  itemKey: string,
  payload: {
    catalog_visible?: boolean;
    category_id?: number | null;
    catalog_item_index?: number | null;
    preview_id?: number | null;
  },
) =>
  apiRequest<FairStandAdminItem>(`${base}/items/${encodeURIComponent(itemKey)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const listFairStandAdminPreviews = () => apiRequest<FairStandAdminPreview[]>(`${base}/previews`);
export const createFairStandAdminPreview = (payload: {
  display_name: string;
  markup: string;
  css_code: string;
  sort_index: number;
  is_active: boolean;
}) => apiRequest<FairStandAdminPreview>(`${base}/previews`, { method: "POST", body: JSON.stringify(payload) });
export const updateFairStandAdminPreview = (
  previewId: number,
  payload: Partial<{
    display_name: string;
    markup: string;
    css_code: string;
    sort_index: number;
    is_active: boolean;
  }>,
) =>
  apiRequest<FairStandAdminPreview>(`${base}/previews/${previewId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminPreview = (previewId: number) =>
  apiRequest<FairStandAdminPreview>(`${base}/previews/${previewId}/archive`, {
    method: "POST",
  });
export const restoreFairStandAdminPreview = (previewId: number) =>
  apiRequest<FairStandAdminPreview>(`${base}/previews/${previewId}/restore`, {
    method: "POST",
  });
