import { apiRequest } from "./client";
import { buildListQueryParams, normalizeStandardListResponse } from "./listTable";
import type { ServerTableFetchParams } from "../hooks/useServerDataTable";
import type { StandardListResponse } from "../types/listTable";

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

export type FairStandAdminStandDimensions = {
  height: number;
  depth: number;
  stripCount: number;
  stripHeight: number;
  frameWidth: number;
  frameDepth: number;
};

export type FairStandAdminRuntimeSettings = {
  maxImageUploadMb: number;
  exportButtonVisible: boolean;
  importButtonVisible: boolean;
};

export type FairStandAdminSettingsBundle = {
  standDimensions: FairStandAdminStandDimensions;
  settings: FairStandAdminRuntimeSettings;
};

export const getFairStandAdminSettings = () =>
  apiRequest<FairStandAdminSettingsBundle>(`${base}/settings`);

export const updateFairStandAdminStandDimensions = (payload: {
  height_m: number;
  depth_m: number;
  strip_count: number;
  strip_height_m: number;
  frame_width_m: number;
  frame_depth_m: number;
}) =>
  apiRequest<FairStandAdminStandDimensions>(`${base}/stand-dimensions`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const updateFairStandAdminRuntimeSettings = (payload: {
  max_image_upload_mb: number;
  export_button_visible: boolean;
  import_button_visible: boolean;
}) =>
  apiRequest<FairStandAdminRuntimeSettings>(`${base}/runtime-settings`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export type FairStandAdminItemRecordSummary = {
  itemKey: string;
  name: string;
  type: string;
  isActive: boolean;
  catalogVisible: boolean;
  categoryId: number | null;
  catalogItemIndex: number | null;
  isRender: boolean;
  componentCount: number;
  assetCount: number;
  hasDimensions: boolean;
  hasSceneDimensions: boolean;
  hasStripOccupancy: boolean;
  hasVideoWall: boolean;
  bodyPartCount: number;
};

export type FairStandAdminItemDimensions = {
  widthCm: number | null;
  depthCm: number | null;
  heightCm: number | null;
  lengthCm: number | null;
  thicknessCm: number | null;
  mountHeightCm: number | null;
  wallGapCm: number | null;
};

export type FairStandAdminItemSceneDimensions = {
  widthCm: number | null;
  depthCm: number | null;
  heightCm: number | null;
};

export type FairStandAdminItemStripOccupancy = {
  align: string;
  stripCount: number;
};

export type FairStandAdminItemAsset = {
  id: string;
  assetRole: string;
  relativePath: string;
  isActive: boolean;
};

export type FairStandAdminItemComponent = {
  id: string;
  childItemKey: string;
  childName: string | null;
  childType: string | null;
  quantity: number;
};

export type FairStandAdminItemBodyPart = {
  id: string;
  bodyRole: string;
  childItemKey: string;
  childName: string | null;
  childType: string | null;
};

export type FairStandAdminItemVideoWall = {
  rows: number;
  cols: number;
  panelItemKey: string;
};

export type FairStandAdminItemRecord = {
  itemKey: string;
  name: string;
  type: string;
  unit: string | null;
  isActive: boolean;
  catalogVisible: boolean;
  categoryId: number | null;
  catalogItemIndex: number | null;
  previewId: number | null;
  material: string | null;
  defaultColor: number | null;
  preserveModelScale: boolean | null;
  modelRotationYDeg: number | null;
  visualRotationYDeg: number | null;
  rotationStepDeg: number | null;
  defaultRotationDeg: number | null;
  sideInsertRotation: string | null;
  compositionMode: string | null;
  paintable: boolean | null;
  shape: string | null;
  variant: string | null;
  eyeCount: number | null;
  defaultZCm: number | null;
  snapTargetItemType: string | null;
  snapAnchor: string | null;
  isRender: boolean;
  acceptsColor: boolean;
  acceptsImage: boolean;
  acceptsLightbox: boolean;
  acceptsGlass: boolean;
  acceptsMesh: boolean;
  dimensions: FairStandAdminItemDimensions | null;
  sceneDimensions: FairStandAdminItemSceneDimensions | null;
  stripOccupancy: FairStandAdminItemStripOccupancy | null;
  assets: FairStandAdminItemAsset[];
  components: FairStandAdminItemComponent[];
  bodyParts: FairStandAdminItemBodyPart[];
  videoWall: FairStandAdminItemVideoWall | null;
};

export type FairStandAdminItemFieldOptions = {
  types: string[];
  units: string[];
  materials: string[];
  shapes: string[];
  variants: string[];
  compositionModes: string[];
  sideInsertRotations: string[];
  snapTargetItemTypes: string[];
  snapAnchors: string[];
};

const EMPTY_FIELD_OPTIONS: FairStandAdminItemFieldOptions = {
  types: [],
  units: [],
  materials: [],
  shapes: [],
  variants: [],
  compositionModes: [],
  sideInsertRotations: [],
  snapTargetItemTypes: [],
  snapAnchors: [],
};

function parseStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim() !== "")
    : [];
}

export type FairStandAdminItemRecordListResponse =
  StandardListResponse<FairStandAdminItemRecordSummary> & {
    filterOptions?: FairStandAdminItemFieldOptions;
  };

export const listFairStandAdminItemRecords = (
  params: Partial<ServerTableFetchParams> = {},
): Promise<FairStandAdminItemRecordListResponse> => {
  const query = buildListQueryParams({
    page: params.page,
    pageSize: params.pageSize,
    search: params.search,
    sortBy: params.sortBy,
    sortOrder: params.sortOrder,
    filters: params.filters,
  });
  return apiRequest<unknown>(`${base}/item-records?${query.toString()}`).then((raw) => {
    const normalized = normalizeStandardListResponse<FairStandAdminItemRecordSummary>(raw);
    const data = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
    const options =
      data.filterOptions && typeof data.filterOptions === "object"
        ? (data.filterOptions as Record<string, unknown>)
        : null;
    return {
      ...normalized,
      filterOptions: {
        types: parseStringList(options?.types),
        units: parseStringList(options?.units),
        materials: parseStringList(options?.materials),
        shapes: parseStringList(options?.shapes),
        variants: parseStringList(options?.variants),
        compositionModes: parseStringList(options?.compositionModes),
        sideInsertRotations: parseStringList(options?.sideInsertRotations),
        snapTargetItemTypes: parseStringList(options?.snapTargetItemTypes),
        snapAnchors: parseStringList(options?.snapAnchors),
      },
    };
  });
};

export const getFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}`);

export const createFairStandAdminItemRecord = (payload: {
  item_key: string;
  name: string;
  item_type: string;
  unit?: string | null;
  catalog_visible?: boolean;
  is_active?: boolean;
  is_render?: boolean;
}) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateFairStandAdminItemRecord = (itemKey: string, payload: Record<string, unknown>) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const archiveFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}/archive`, {
    method: "POST",
  });

export const restoreFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}/restore`, {
    method: "POST",
  });
