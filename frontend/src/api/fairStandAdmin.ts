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
  heightCm: number;
  depthCm: number;
  frameWidthCm: number;
  frameDepthCm: number;
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
  height_cm: number;
  depth_cm: number;
  frame_width_cm: number;
  frame_depth_cm: number;
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
  familyId: number | null;
  familyCode: string | null;
  snapRequiresRuleId: number | null;
  snapProvidesRuleId: number | null;
  snapRequires: string | null;
  snapProvides: string | null;
  snapFace: string | null;
  snapEdge: string | null;
  snapMountMode: string | null;
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

export type FairStandAdminSnapRuleOption = {
  id: number;
  code: string;
  displayName: string;
  face: string | null;
  edge: string | null;
  mountMode: string | null;
};

export type FairStandAdminFamilyOption = {
  id: number;
  code: string;
  displayName: string;
};

export type FairStandAdminItemFieldOptions = {
  types: string[];
  units: string[];
  materials: string[];
  shapes: string[];
  variants: string[];
  compositionModes: string[];
  sideInsertRotations: string[];
  snapFaces: string[];
  snapEdges: string[];
  families: FairStandAdminFamilyOption[];
  snapRules: FairStandAdminSnapRuleOption[];
};

const EMPTY_FIELD_OPTIONS: FairStandAdminItemFieldOptions = {
  types: [],
  units: [],
  materials: [],
  shapes: [],
  variants: [],
  compositionModes: [],
  sideInsertRotations: [],
  snapFaces: [],
  snapEdges: [],
  families: [],
  snapRules: [],
};

function parseStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim() !== "")
    : [];
}

function parseFamilyOptions(value: unknown): FairStandAdminFamilyOption[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = entry as Record<string, unknown>;
      const id = Number(row.id);
      if (!Number.isFinite(id)) return null;
      return {
        id,
        code: String(row.code ?? ""),
        displayName: String(row.displayName ?? row.code ?? ""),
      };
    })
    .filter((row): row is FairStandAdminFamilyOption => row !== null);
}

function parseSnapRuleOptions(value: unknown): FairStandAdminSnapRuleOption[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = entry as Record<string, unknown>;
      const id = Number(row.id);
      if (!Number.isFinite(id)) return null;
      return {
        id,
        code: String(row.code ?? ""),
        displayName: String(row.displayName ?? row.code ?? ""),
        face: row.face == null ? null : String(row.face),
        edge: row.edge == null ? null : String(row.edge),
        mountMode: row.mountMode == null ? null : String(row.mountMode),
      };
    })
    .filter((row): row is FairStandAdminSnapRuleOption => row !== null);
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
        snapFaces: parseStringList(options?.snapFaces),
        snapEdges: parseStringList(options?.snapEdges),
        families: parseFamilyOptions(options?.families),
        snapRules: parseSnapRuleOptions(options?.snapRules),
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

export type FairStandAdminFamily = {
  id: number;
  code: string;
  displayName: string;
  sortIndex: number;
  isActive: boolean;
};

export type FairStandAdminRuleType = {
  id: number;
  code: string;
  displayName: string;
  isActive: boolean;
};

export type FairStandAdminRule = {
  id: number;
  ruleTypeId: number;
  ruleTypeCode: string | null;
  code: string;
  displayName: string;
  face: string | null;
  edge: string | null;
  mountMode: string | null;
  sortIndex: number;
  isActive: boolean;
};

export const listFairStandAdminFamilies = () => apiRequest<FairStandAdminFamily[]>(`${base}/families`);
export const createFairStandAdminFamily = (payload: {
  code: string;
  display_name: string;
  sort_index?: number;
  is_active?: boolean;
}) => apiRequest<FairStandAdminFamily>(`${base}/families`, { method: "POST", body: JSON.stringify(payload) });
export const updateFairStandAdminFamily = (
  familyId: number,
  payload: Partial<{ code: string; display_name: string; sort_index: number; is_active: boolean }>,
) =>
  apiRequest<FairStandAdminFamily>(`${base}/families/${familyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminFamily = (familyId: number) =>
  apiRequest<FairStandAdminFamily>(`${base}/families/${familyId}/archive`, { method: "POST" });
export const restoreFairStandAdminFamily = (familyId: number) =>
  apiRequest<FairStandAdminFamily>(`${base}/families/${familyId}/restore`, { method: "POST" });

export const listFairStandAdminRuleTypes = () =>
  apiRequest<FairStandAdminRuleType[]>(`${base}/rule-types`);
export const createFairStandAdminRuleType = (payload: {
  code: string;
  display_name: string;
  is_active?: boolean;
}) =>
  apiRequest<FairStandAdminRuleType>(`${base}/rule-types`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateFairStandAdminRuleType = (
  ruleTypeId: number,
  payload: Partial<{ code: string; display_name: string; is_active: boolean }>,
) =>
  apiRequest<FairStandAdminRuleType>(`${base}/rule-types/${ruleTypeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminRuleType = (ruleTypeId: number) =>
  apiRequest<FairStandAdminRuleType>(`${base}/rule-types/${ruleTypeId}/archive`, { method: "POST" });
export const restoreFairStandAdminRuleType = (ruleTypeId: number) =>
  apiRequest<FairStandAdminRuleType>(`${base}/rule-types/${ruleTypeId}/restore`, { method: "POST" });

export const listFairStandAdminRules = () => apiRequest<FairStandAdminRule[]>(`${base}/rules`);
export const createFairStandAdminRule = (payload: {
  rule_type_id: number;
  code: string;
  display_name: string;
  face?: string | null;
  edge?: string | null;
  mount_mode?: string | null;
  sort_index?: number;
  is_active?: boolean;
}) => apiRequest<FairStandAdminRule>(`${base}/rules`, { method: "POST", body: JSON.stringify(payload) });
export const updateFairStandAdminRule = (
  ruleId: number,
  payload: Partial<{
    rule_type_id: number;
    code: string;
    display_name: string;
    face: string | null;
    edge: string | null;
    mount_mode: string | null;
    sort_index: number;
    is_active: boolean;
  }>,
) =>
  apiRequest<FairStandAdminRule>(`${base}/rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminRule = (ruleId: number) =>
  apiRequest<FairStandAdminRule>(`${base}/rules/${ruleId}/archive`, { method: "POST" });
export const restoreFairStandAdminRule = (ruleId: number) =>
  apiRequest<FairStandAdminRule>(`${base}/rules/${ruleId}/restore`, { method: "POST" });
