import { apiRequest, ApiError } from "./client";
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
  panelRailHeightCm: number;
};

export type FairStandAdminRuntimeSettings = {
  maxImageUploadMb: number;
  exportButtonVisible: boolean;
  importButtonVisible: boolean;
  saveAsButtonVisible: boolean;
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
  panel_rail_height_cm: number;
}) =>
  apiRequest<FairStandAdminStandDimensions>(`${base}/stand-dimensions`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const updateFairStandAdminRuntimeSettings = (payload: {
  max_image_upload_mb: number;
  export_button_visible: boolean;
  import_button_visible: boolean;
  save_as_button_visible: boolean;
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

export type FairStandAdminItemAssemblyPart = {
  id?: string;
  childItemKey: string;
  instanceIndex: number;
  xCm: number;
  yCm: number;
  zCm: number;
  rotationXDeg: number;
  rotationYDeg: number;
  rotationZDeg: number;
  lockGroupId?: number | null;
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
  snapRequiresRuleId: number | null;
  snapProvidesRuleId: number | null;
  snapRequires: string | null;
  snapProvides: string | null;
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
  assemblyParts: FairStandAdminItemAssemblyPart[];
  bodyParts: FairStandAdminItemBodyPart[];
  videoWall: FairStandAdminItemVideoWall | null;
};

export type FairStandAdminSnapRuleOption = {
  id: number;
  key: string;
  displayName: string;
  face: string | null;
  edge: string | null;
};

export type FairStandAdminItemTypeOption = {
  id: number;
  key: string;
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
  itemTypes: FairStandAdminItemTypeOption[];
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
  itemTypes: [],
  snapRules: [],
};

function parseStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim() !== "")
    : [];
}

function parseItemTypeOptions(value: unknown): FairStandAdminItemTypeOption[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = entry as Record<string, unknown>;
      const id = Number(row.id);
      if (!Number.isFinite(id)) return null;
      return {
        id,
        key: String(row.key ?? row.code ?? ""),
        displayName: String(row.displayName ?? row.key ?? row.code ?? ""),
      };
    })
    .filter((row): row is FairStandAdminItemTypeOption => row !== null);
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
        key: String(row.key ?? row.code ?? ""),
        displayName: String(row.displayName ?? row.key ?? row.code ?? ""),
        face: row.face == null ? null : String(row.face),
        edge: row.edge == null ? null : String(row.edge),
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
        itemTypes: parseItemTypeOptions(options?.itemTypes),
        snapRules: parseSnapRuleOptions(options?.snapRules),
      },
    };
  });
};

export const getFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}`);

/** True if item_key already exists (same check as create uniqueness). */
export async function fairStandAdminItemKeyExists(itemKey: string): Promise<boolean> {
  try {
    await getFairStandAdminItemRecord(itemKey);
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return false;
    throw error;
  }
}

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

export const cloneFairStandAdminItemRecord = (
  sourceItemKey: string,
  payload: { item_key: string; name: string },
) =>
  apiRequest<FairStandAdminItemRecord>(
    `${base}/item-records/${encodeURIComponent(sourceItemKey)}/clone`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const updateFairStandAdminItemRecord = (itemKey: string, payload: Record<string, unknown>) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const updateFairStandAdminItemAssembly = (
  itemKey: string,
  payload: {
    parts: Array<{
      child_item_key: string;
      instance_index: number;
      x_cm: number;
      y_cm: number;
      z_cm: number;
      rotation_x_deg: number;
      rotation_y_deg: number;
      rotation_z_deg: number;
      lock_group_id?: number | null;
    }>;
  },
) =>
  apiRequest<FairStandAdminItemRecord>(
    `${base}/item-records/${encodeURIComponent(itemKey)}/assembly`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

export const archiveFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}/archive`, {
    method: "POST",
  });

export const restoreFairStandAdminItemRecord = (itemKey: string) =>
  apiRequest<FairStandAdminItemRecord>(`${base}/item-records/${encodeURIComponent(itemKey)}/restore`, {
    method: "POST",
  });

export type FairStandAdminItemType = {
  id: number;
  key: string;
  displayName: string;
  placement: string;
  collision: string;
  moveSnapCm: number;
  magneticSnap: string;
  allowSideInsert: boolean;
  supportsWallOverlayMount: boolean;
  wallCapacity: string;
  connectionEndpoint: string;
  collisionDepth: string;
  endpointContact: string;
  boundarySnap: string;
  collisionHeight: string;
  overlapWithTypes: string[];
  overlapItemTypeIds: number[];
  ghost: {
    kind: string;
    renderer: string;
    opacity: number;
  };
  isActive: boolean;
};

export type FairStandAdminRuleType = {
  id: number;
  key: string;
  displayName: string;
  isActive: boolean;
};

export type FairStandAdminRule = {
  id: number;
  ruleTypeId: number;
  ruleTypeKey: string | null;
  key: string;
  displayName: string;
  face: string | null;
  edge: string | null;
  itemTypeIds: number[];
  itemTypeKeys: string[];
  isActive: boolean;
};

export const listFairStandAdminItemTypes = () =>
  apiRequest<FairStandAdminItemType[]>(`${base}/item-types`);
export const createFairStandAdminItemType = (payload: {
  display_name: string;
  key?: string | null;
  is_active?: boolean;
  placement?: string | null;
  collision?: string | null;
  move_snap_cm?: number | null;
  magnetic_snap?: string | null;
  allow_side_insert?: boolean | null;
  supports_wall_overlay_mount?: boolean | null;
  wall_capacity?: string | null;
  connection_endpoint?: string | null;
  collision_depth?: string | null;
  endpoint_contact?: string | null;
  boundary_snap?: string | null;
  collision_height?: string | null;
  overlap_with_types?: string[] | null;
  overlap_item_type_ids?: number[] | null;
  ghost_kind?: string | null;
  ghost_renderer?: string | null;
  ghost_opacity?: number | null;
}) =>
  apiRequest<FairStandAdminItemType>(`${base}/item-types`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateFairStandAdminItemType = (
  itemTypeId: number,
  payload: Partial<{
    key: string;
    display_name: string;
    is_active: boolean;
    placement: string;
    collision: string;
    move_snap_cm: number;
    magnetic_snap: string;
    allow_side_insert: boolean;
    supports_wall_overlay_mount: boolean;
    wall_capacity: string;
    connection_endpoint: string;
    collision_depth: string;
    endpoint_contact: string;
    boundary_snap: string;
    collision_height: string;
    overlap_with_types: string[];
    overlap_item_type_ids: number[];
    ghost_kind: string;
    ghost_renderer: string;
    ghost_opacity: number;
  }>,
) =>
  apiRequest<FairStandAdminItemType>(`${base}/item-types/${itemTypeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const archiveFairStandAdminItemType = (itemTypeId: number) =>
  apiRequest<FairStandAdminItemType>(`${base}/item-types/${itemTypeId}/archive`, {
    method: "POST",
  });
export const restoreFairStandAdminItemType = (itemTypeId: number) =>
  apiRequest<FairStandAdminItemType>(`${base}/item-types/${itemTypeId}/restore`, {
    method: "POST",
  });

export const listFairStandAdminRuleTypes = () =>
  apiRequest<FairStandAdminRuleType[]>(`${base}/rule-types`);
export const createFairStandAdminRuleType = (payload: {
  key?: string | null;
  display_name: string;
  is_active?: boolean;
}) =>
  apiRequest<FairStandAdminRuleType>(`${base}/rule-types`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateFairStandAdminRuleType = (
  ruleTypeId: number,
  payload: Partial<{ key: string; display_name: string; is_active: boolean }>,
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
  key?: string | null;
  display_name: string;
  face?: string | null;
  edge?: string | null;
  item_type_ids?: number[];
  is_active?: boolean;
}) => apiRequest<FairStandAdminRule>(`${base}/rules`, { method: "POST", body: JSON.stringify(payload) });
export const updateFairStandAdminRule = (
  ruleId: number,
  payload: Partial<{
    rule_type_id: number;
    key: string;
    display_name: string;
    face: string | null;
    edge: string | null;
    item_type_ids: number[];
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
