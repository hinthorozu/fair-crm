import React from "react";
import {
  archiveFairStandAdminItemRecord,
  createFairStandAdminItemRecord,
  getFairStandAdminItemRecord,
  listFairStandAdminCategories,
  listFairStandAdminItemRecords,
  listFairStandAdminPreviews,
  restoreFairStandAdminItemRecord,
  updateFairStandAdminItemRecord,
  type FairStandAdminCategory,
  type FairStandAdminItemRecord,
  type FairStandAdminItemAsset,
  type FairStandAdminItemBodyPart,
  type FairStandAdminItemComponent,
  type FairStandAdminItemFieldOptions,
  type FairStandAdminItemRecordSummary,
  type FairStandAdminPreview,
} from "../api/fairStandAdmin";
import { FairStandCatalogPreviewSelect } from "../components/FairStandCatalogPreviewSelect";
import { FairStandCatalogLivePreview } from "../components/fairStand/FairStandCatalogLivePreview";
import { FairStandItemEntitySelect } from "../components/FairStandItemEntitySelect";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DetailValue } from "../components/ui/DetailFields";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { TableRowActions } from "../components/ui/TableRowActions";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import {
  CheckboxField,
  FormActions,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextInput,
  useFormDirtyCancel,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  FAIR_STAND_ITEMS_ARCHIVE,
  FAIR_STAND_ITEMS_CREATE,
  FAIR_STAND_ITEMS_READ,
  FAIR_STAND_ITEMS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type CreateForm = {
  item_key: string;
  name: string;
  item_type: string;
};

type AssetFormRow = { asset_role: string; relative_path: string; is_active: boolean };
type ComponentFormRow = {
  child_item_key: string;
  child_name: string;
  child_type: string;
  quantity: string;
};
type BodyPartFormRow = {
  body_role: string;
  child_item_key: string;
  child_name: string;
  child_type: string;
};

type EditForm = {
  name: string;
  item_type: string;
  unit: string;
  material: string;
  shape: string;
  variant: string;
  composition_mode: string;
  side_insert_rotation: string;
  snap_requires_rule_id: string;
  snap_provides_rule_id: string;
  default_z_cm: string;
  default_color: string;
  eye_count: string;
  model_rotation_y_deg: string;
  visual_rotation_y_deg: string;
  rotation_step_deg: string;
  default_rotation_deg: string;
  is_active: boolean;
  is_render: boolean;
  preserve_model_scale: boolean;
  paintable: boolean;
  accepts_color: boolean;
  accepts_image: boolean;
  accepts_lightbox: boolean;
  accepts_glass: boolean;
  accepts_mesh: boolean;
  catalog_visible: boolean;
  category_id: string;
  catalog_item_index: string;
  preview_id: string;
  width_cm: string;
  depth_cm: string;
  height_cm: string;
  mount_height_cm: string;
  wall_gap_cm: string;
  scene_width_cm: string;
  scene_depth_cm: string;
  scene_height_cm: string;
  strip_align: string;
  strip_count: string;
  assets: AssetFormRow[];
  components: ComponentFormRow[];
  body_parts: BodyPartFormRow[];
  video_rows: string;
  video_cols: string;
  panel_item_key: string;
};

const emptyCreate: CreateForm = { item_key: "", name: "", item_type: "" };

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

function itemTypeSelectOptions(
  itemTypes: FairStandAdminItemFieldOptions["itemTypes"],
  selectedKey: string,
): React.ReactNode {
  const keys = new Set(itemTypes.map((row) => row.key));
  return (
    <>
      <option value="">{adminLabels.fairStandCatalogSelectPlaceholder}</option>
      {selectedKey && !keys.has(selectedKey) ? <option value={selectedKey}>{selectedKey}</option> : null}
      {itemTypes.map((itemType) => (
        <option key={itemType.key} value={itemType.key}>
          {itemType.displayName} ({itemType.key})
        </option>
      ))}
    </>
  );
}

function SuggestTextInput({
  id,
  listId,
  options,
  value,
  disabled,
  required,
  type,
  onChange,
}: {
  id: string;
  listId: string;
  options: string[];
  value: string;
  disabled?: boolean;
  required?: boolean;
  type?: string;
  onChange: (value: string) => void;
}) {
  return (
    <>
      <TextInput
        id={id}
        list={listId}
        type={type}
        value={value}
        disabled={disabled}
        required={required}
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}

const ITEM_KEY_TR_MAP: Record<string, string> = {
  ç: "c",
  Ç: "c",
  ğ: "g",
  Ğ: "g",
  ı: "i",
  İ: "i",
  ö: "o",
  Ö: "o",
  ş: "s",
  Ş: "s",
  ü: "u",
  Ü: "u",
};

function slugifyItemKey(name: string): string {
  const ascii = Array.from(name)
    .map((char) => ITEM_KEY_TR_MAP[char] ?? char)
    .join("")
    .toLowerCase();
  return ascii
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 128);
}

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function str(value: string | number | null | undefined): string {
  return value == null ? "" : String(value);
}

function optionalNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) {
    throw new Error(adminLabels.fairStandSettingsValidationPositiveNumber.replace("{label}", trimmed));
  }
  return value;
}

function optionalInt(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  if (!Number.isInteger(value)) {
    throw new Error(adminLabels.fairStandSettingsValidationPositiveInt.replace("{label}", trimmed));
  }
  return value;
}

function requireText(raw: string, label: string): string {
  const value = raw.trim();
  if (!value) {
    throw new Error(adminLabels.fairStandItemsValidationRequired.replace("{label}", label));
  }
  return value;
}

function hasAny(...values: string[]): boolean {
  return values.some((value) => value.trim() !== "");
}

function detailToForm(detail: FairStandAdminItemRecord): EditForm {
  const dims = detail.dimensions;
  const scene = detail.sceneDimensions;
  const strip = detail.stripOccupancy;
  const video = detail.videoWall;
  return {
    name: detail.name,
    item_type: detail.type,
    unit: str(detail.unit),
    material: str(detail.material),
    shape: str(detail.shape),
    variant: str(detail.variant),
    composition_mode: str(detail.compositionMode),
    side_insert_rotation: str(detail.sideInsertRotation),
    snap_requires_rule_id: str(detail.snapRequiresRuleId),
    snap_provides_rule_id: str(detail.snapProvidesRuleId),
    default_z_cm: str(detail.defaultZCm),
    default_color: str(detail.defaultColor),
    eye_count: str(detail.eyeCount),
    model_rotation_y_deg: str(detail.modelRotationYDeg),
    visual_rotation_y_deg: str(detail.visualRotationYDeg),
    rotation_step_deg: str(detail.rotationStepDeg),
    default_rotation_deg: str(detail.defaultRotationDeg),
    is_active: detail.isActive,
    is_render: detail.isRender,
    preserve_model_scale: Boolean(detail.preserveModelScale),
    paintable: Boolean(detail.paintable),
    accepts_color: detail.acceptsColor,
    accepts_image: detail.acceptsImage,
    accepts_lightbox: detail.acceptsLightbox,
    accepts_glass: detail.acceptsGlass,
    accepts_mesh: detail.acceptsMesh,
    catalog_visible: detail.catalogVisible,
    category_id: str(detail.categoryId),
    catalog_item_index: str(detail.catalogItemIndex),
    preview_id: str(detail.previewId),
    width_cm: str(dims?.widthCm),
    depth_cm: str(dims?.depthCm),
    height_cm: str(dims?.heightCm),
    mount_height_cm: str(dims?.mountHeightCm),
    wall_gap_cm: str(dims?.wallGapCm),
    scene_width_cm: str(scene?.widthCm),
    scene_depth_cm: str(scene?.depthCm),
    scene_height_cm: str(scene?.heightCm),
    strip_align: strip?.align ?? "",
    strip_count: str(strip?.stripCount),
    assets: detail.assets.map((asset) => ({
      asset_role: asset.assetRole,
      relative_path: asset.relativePath,
      is_active: asset.isActive,
    })),
    components: detail.components.map((component) => ({
      child_item_key: component.childItemKey,
      child_name: component.childName ?? "",
      child_type: component.childType ?? "",
      quantity: str(component.quantity),
    })),
    body_parts: detail.bodyParts.map((part) => ({
      body_role: part.bodyRole,
      child_item_key: part.childItemKey,
      child_name: part.childName ?? "",
      child_type: part.childType ?? "",
    })),
    video_rows: str(video?.rows),
    video_cols: str(video?.cols),
    panel_item_key: str(video?.panelItemKey),
  };
}

function buildUpdatePayload(form: EditForm): Record<string, unknown> {
  const dimensions = hasAny(
    form.width_cm,
    form.depth_cm,
    form.height_cm,
    form.mount_height_cm,
    form.wall_gap_cm,
  )
    ? {
        width_cm: optionalNumber(form.width_cm),
        depth_cm: optionalNumber(form.depth_cm),
        height_cm: optionalNumber(form.height_cm),
        mount_height_cm: optionalNumber(form.mount_height_cm),
        wall_gap_cm: optionalNumber(form.wall_gap_cm),
      }
    : null;

  const scene_dimensions = hasAny(form.scene_width_cm, form.scene_depth_cm, form.scene_height_cm)
    ? {
        width_cm: optionalNumber(form.scene_width_cm),
        depth_cm: optionalNumber(form.scene_depth_cm),
        height_cm: optionalNumber(form.scene_height_cm),
      }
    : null;

  const strip_occupancy = hasAny(form.strip_align, form.strip_count)
    ? {
        align: form.strip_align.trim() || "top",
        strip_count: optionalInt(form.strip_count) ?? 0,
      }
    : null;

  const video_wall = hasAny(form.video_rows, form.video_cols, form.panel_item_key)
    ? {
        rows: optionalInt(form.video_rows) ?? 0,
        cols: optionalInt(form.video_cols) ?? 0,
        panel_item_key: form.panel_item_key.trim(),
      }
    : null;

  return {
    name: requireText(form.name, adminLabels.fairStandItemsFieldName),
    item_type: requireText(form.item_type, adminLabels.fairStandItemsFieldItemType),
    unit: form.unit.trim() || null,
    material: form.material.trim() || null,
    shape: form.shape.trim() || null,
    variant: form.variant.trim() || null,
    composition_mode: form.composition_mode.trim() || null,
    side_insert_rotation: form.side_insert_rotation.trim() || null,
    snap_requires_rule_id: optionalInt(form.snap_requires_rule_id),
    snap_provides_rule_id: optionalInt(form.snap_provides_rule_id),
    default_z_cm: optionalNumber(form.default_z_cm) ?? 0,
    default_color: optionalInt(form.default_color),
    eye_count: optionalInt(form.eye_count),
    model_rotation_y_deg: optionalNumber(form.model_rotation_y_deg),
    visual_rotation_y_deg: optionalNumber(form.visual_rotation_y_deg),
    rotation_step_deg: optionalNumber(form.rotation_step_deg),
    default_rotation_deg: optionalNumber(form.default_rotation_deg),
    is_active: form.is_active,
    is_render: form.is_render,
    preserve_model_scale: form.preserve_model_scale,
    paintable: form.paintable,
    accepts_color: form.accepts_color,
    accepts_image: form.accepts_image,
    accepts_lightbox: form.accepts_lightbox,
    accepts_glass: form.accepts_glass,
    accepts_mesh: form.accepts_mesh,
    catalog_visible: form.catalog_visible,
    category_id: optionalInt(form.category_id),
    catalog_item_index: optionalInt(form.catalog_item_index),
    preview_id: optionalInt(form.preview_id),
    dimensions,
    scene_dimensions,
    strip_occupancy,
    assets: form.assets.map((asset) => ({
      asset_role: requireText(asset.asset_role, adminLabels.fairStandItemsFieldAssetRole),
      relative_path: requireText(asset.relative_path, adminLabels.fairStandItemsFieldRelativePath),
      is_active: asset.is_active,
    })),
    components: form.components.map((component) => ({
      child_item_key: requireText(component.child_item_key, adminLabels.fairStandItemsFieldChildItemKey),
      quantity: optionalNumber(component.quantity) ?? 0,
    })),
    body_parts: form.body_parts.map((part) => ({
      body_role: requireText(part.body_role, adminLabels.fairStandItemsFieldBodyRole),
      child_item_key: requireText(part.child_item_key, adminLabels.fairStandItemsFieldChildItemKey),
    })),
    video_wall,
  };
}

function YesNoBadge({ value }: { value: boolean | null | undefined }) {
  if (value == null) return <DetailValue value={null} />;
  return (
    <Badge variant={value ? "success" : "neutral"}>
      {value ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo}
    </Badge>
  );
}

function DetailItem({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        {children}
        {hint ? <span className="field-hint">{hint}</span> : null}
      </dd>
    </div>
  );
}

type ItemsRoute =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "detail"; itemKey: string }
  | { kind: "edit"; itemKey: string };

const ITEMS_BASE_PATH = "/admin/fair-stand/items";
const ITEMS_FLASH_KEY = "fair-stand-items-flash";

function itemsListPath(): string {
  return ITEMS_BASE_PATH;
}

function itemsCreatePath(): string {
  return `${ITEMS_BASE_PATH}/new`;
}

function itemsDetailPath(itemKey: string): string {
  return `${ITEMS_BASE_PATH}/${encodeURIComponent(itemKey)}`;
}

function itemsEditPath(itemKey: string): string {
  return `${ITEMS_BASE_PATH}/${encodeURIComponent(itemKey)}/edit`;
}

function normalizePathname(pathname: string): string {
  const trimmed = pathname.replace(/\/$/, "");
  return trimmed || "/";
}

function parseItemsRoute(pathname: string): ItemsRoute {
  const path = normalizePathname(pathname);
  if (path === ITEMS_BASE_PATH) return { kind: "list" };
  if (path === `${ITEMS_BASE_PATH}/new`) return { kind: "create" };
  const editMatch = path.match(/^\/admin\/fair-stand\/items\/([^/]+)\/edit$/);
  if (editMatch) {
    return { kind: "edit", itemKey: decodeURIComponent(editMatch[1]) };
  }
  const detailMatch = path.match(/^\/admin\/fair-stand\/items\/([^/]+)$/);
  if (detailMatch && detailMatch[1] !== "new") {
    return { kind: "detail", itemKey: decodeURIComponent(detailMatch[1]) };
  }
  return { kind: "list" };
}

function setItemsFlash(message: string): void {
  sessionStorage.setItem(ITEMS_FLASH_KEY, message);
}

function takeItemsFlash(): string | null {
  const message = sessionStorage.getItem(ITEMS_FLASH_KEY);
  if (message) sessionStorage.removeItem(ITEMS_FLASH_KEY);
  return message;
}

type DetailTabId = "general" | "dimensions" | "components" | "assets";

export function FairStandItemsAdminPage() {
  const [pathname, setPathname] = React.useState(() =>
    normalizePathname(window.location.pathname),
  );
  const route = React.useMemo(() => parseItemsRoute(pathname), [pathname]);
  const listUrlRef = React.useRef(itemsListPath());

  React.useEffect(() => {
    const onPopState = () => setPathname(normalizePathname(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigateTo = React.useCallback((path: string) => {
    const next = path.startsWith("/") ? path : `/${path}`;
    if (`${window.location.pathname}${window.location.search}` !== next) {
      window.history.pushState(null, "", next);
    }
    setPathname(normalizePathname(next.split("?")[0] ?? next));
  }, []);

  React.useEffect(() => {
    if (route.kind === "list") {
      listUrlRef.current = `${window.location.pathname}${window.location.search}`;
    }
  }, [route.kind, pathname]);

  const backToList = React.useCallback(() => {
    navigateTo(listUrlRef.current || itemsListPath());
  }, [navigateTo]);

  if (route.kind === "list") {
    return (
      <ItemsListPage
        onOpenCreate={() => navigateTo(itemsCreatePath())}
        onOpenDetail={(itemKey) => navigateTo(itemsDetailPath(itemKey))}
      />
    );
  }
  if (route.kind === "create") {
    return (
      <ItemsCreatePage
        onCancel={backToList}
        onCreated={(itemKey) => {
          setItemsFlash(adminLabels.fairStandItemsSaveSuccess);
          navigateTo(itemsDetailPath(itemKey));
        }}
      />
    );
  }
  if (route.kind === "detail") {
    return (
      <ItemsDetailPage
        itemKey={route.itemKey}
        onBack={backToList}
        onEdit={(key) => navigateTo(itemsEditPath(key))}
      />
    );
  }
  return (
    <ItemsEditPage
      itemKey={route.itemKey}
      onCancel={(key) => navigateTo(itemsDetailPath(key))}
      onSaved={(key) => {
        setItemsFlash(adminLabels.fairStandItemsSaveSuccess);
        navigateTo(itemsDetailPath(key));
      }}
    />
  );
}

function ItemsListPage({
  onOpenCreate,
  onOpenDetail,
}: {
  onOpenCreate: () => void;
  onOpenDetail: (itemKey: string) => void;
}) {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_ITEMS_READ);
  const canCreate = granted.has(FAIR_STAND_ITEMS_CREATE);
  const canArchive = granted.has(FAIR_STAND_ITEMS_ARCHIVE);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(() => takeItemsFlash());
  const [archiveTargetKey, setArchiveTargetKey] = React.useState<string | null>(null);
  const [fieldOptions, setFieldOptions] =
    React.useState<FairStandAdminItemFieldOptions>(EMPTY_FIELD_OPTIONS);

  const table = useServerDataTable<FairStandAdminItemRecordSummary>({
    fetchFn: async (params) => {
      const response = await listFairStandAdminItemRecords(params);
      if (response.filterOptions) {
        setFieldOptions(response.filterOptions);
      }
      return response;
    },
    enabled: canRead,
    filterKeys: ["catalog", "render", "type"],
    defaultSort: { field: "itemKey", direction: "asc" },
    urlSync: true,
    urlPath: ITEMS_BASE_PATH,
  });

  const handleArchive = async (itemKey: string) => {
    try {
      await archiveFairStandAdminItemRecord(itemKey);
      setArchiveTargetKey(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      setError(null);
      await table.refresh();
    } catch (archiveError) {
      setArchiveTargetKey(null);
      setSuccess(null);
      setError(
        archiveError instanceof Error ? archiveError.message : adminLabels.fairStandItemsArchiveError,
      );
    }
  };

  const handleRestore = async (itemKey: string) => {
    try {
      await restoreFairStandAdminItemRecord(itemKey);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      setError(null);
      await table.refresh();
    } catch (restoreError) {
      setSuccess(null);
      setError(
        restoreError instanceof Error ? restoreError.message : adminLabels.fairStandItemsRestoreError,
      );
    }
  };

  const columns: UniversalDataTableColumn<FairStandAdminItemRecordSummary>[] = [
    {
      key: "itemKey",
      title: adminLabels.fairStandItemsColItemKey,
      sortable: true,
      render: (row) => row.itemKey,
    },
    {
      key: "name",
      title: adminLabels.fairStandItemsColName,
      sortable: true,
      render: (row) => row.name,
    },
    {
      key: "type",
      title: adminLabels.fairStandItemsColType,
      sortable: true,
      render: (row) => row.type,
    },
    {
      key: "catalogVisible",
      title: adminLabels.fairStandItemsColCatalogVisible,
      sortable: true,
      render: (row) => (
        <Badge variant={row.catalogVisible ? "success" : "neutral"}>
          {row.catalogVisible ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo}
        </Badge>
      ),
    },
    {
      key: "isRender",
      title: adminLabels.fairStandItemsColIsRender,
      sortable: true,
      render: (row) => (
        <Badge variant={row.isRender ? "success" : "neutral"}>
          {row.isRender ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo}
        </Badge>
      ),
    },
    {
      key: "status",
      title: adminLabels.fairStandItemsColStatus,
      sortable: true,
      render: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive
            ? adminLabels.fairStandItemsStatusActive
            : adminLabels.fairStandItemsStatusInactive}
        </Badge>
      ),
    },
    {
      key: "actions",
      title: adminLabels.fairStandItemsColActions,
      sortable: false,
      render: (row) => (
        <TableRowActions>
          <button type="button" className="btn link" onClick={() => onOpenDetail(row.itemKey)}>
            {adminLabels.fairStandItemsActionView}
          </button>
          {canArchive && row.isActive ? (
            <button
              type="button"
              className="btn link danger"
              onClick={() => setArchiveTargetKey(row.itemKey)}
            >
              {adminLabels.fairStandItemsActionArchive}
            </button>
          ) : null}
          {canArchive && !row.isActive ? (
            <button
              type="button"
              className="btn link"
              onClick={() => {
                void handleRestore(row.itemKey);
              }}
            >
              {adminLabels.fairStandItemsActionRestore}
            </button>
          ) : null}
        </TableRowActions>
      ),
    },
  ];

  return (
    <PageShell>
      <PageHeader
        title={adminLabels.fairStandItemsTitle}
        subtitle={adminLabels.fairStandItemsSubtitle}
        actions={
          canCreate ? (
            <Button variant="primary" onClick={onOpenCreate}>
              {adminLabels.fairStandItemsCreate}
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandItemsPermissionDenied}</Banner> : null}
      {canRead ? (
        <UniversalDataTable
          table={table}
          columns={columns}
          rowKey={(row) => row.itemKey}
          toolbar={
            <FilterPanel
              actions={
                <Button variant="secondary" onClick={() => void table.refresh()}>
                  {adminLabels.fairStandItemsRefresh}
                </Button>
              }
            >
              <FormField label={adminLabels.fairStandItemsFilterSearch} htmlFor="fs-items-search">
                <TextInput
                  id="fs-items-search"
                  value={table.search}
                  placeholder={adminLabels.fairStandItemsFilterSearchPlaceholder}
                  onChange={(event) => table.setSearch(event.target.value)}
                />
              </FormField>
              <FormField label={adminLabels.fairStandItemsFilterCatalog} htmlFor="fs-items-catalog">
                <SelectInput
                  id="fs-items-catalog"
                  value={table.filters.catalog ?? "all"}
                  onChange={(event) => table.setFilter("catalog", event.target.value)}
                >
                  <option value="all">{adminLabels.fairStandItemsFilterAll}</option>
                  <option value="visible">{adminLabels.fairStandItemsFilterCatalogVisible}</option>
                  <option value="hidden">{adminLabels.fairStandItemsFilterCatalogHidden}</option>
                </SelectInput>
              </FormField>
              <FormField label={adminLabels.fairStandItemsFilterRender} htmlFor="fs-items-render">
                <SelectInput
                  id="fs-items-render"
                  value={table.filters.render ?? "all"}
                  onChange={(event) => table.setFilter("render", event.target.value)}
                >
                  <option value="all">{adminLabels.fairStandItemsFilterAll}</option>
                  <option value="yes">{adminLabels.fairStandItemsFilterRenderYes}</option>
                  <option value="no">{adminLabels.fairStandItemsFilterRenderNo}</option>
                </SelectInput>
              </FormField>
              <FormField label={adminLabels.fairStandItemsFilterType} htmlFor="fs-items-type">
                <SelectInput
                  id="fs-items-type"
                  value={table.filters.type ?? "all"}
                  onChange={(event) => table.setFilter("type", event.target.value)}
                >
                  <option value="all">{adminLabels.fairStandItemsFilterAll}</option>
                      {fieldOptions.types.map((itemType) => (
                        <option key={itemType} value={itemType}>
                          {itemType}
                        </option>
                      ))}
                </SelectInput>
              </FormField>
            </FilterPanel>
          }
          emptyState={
            <EmptyState
              title={adminLabels.fairStandItemsEmptyTitle}
              description={adminLabels.fairStandItemsEmptyDescription}
            />
          }
        />
      ) : null}
      {archiveTargetKey ? (
        <ConfirmDialog
          title={adminLabels.fairStandItemsArchiveConfirmTitle}
          message={adminLabels.fairStandItemsArchiveConfirmMessage}
          confirmLabel={adminLabels.fairStandItemsArchiveConfirm}
          cancelLabel={adminLabels.fairStandItemsCancel}
          onCancel={() => setArchiveTargetKey(null)}
          onConfirm={() => {
            void handleArchive(archiveTargetKey);
          }}
        />
      ) : null}
    </PageShell>
  );
}

function ItemsCreatePage({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (itemKey: string) => void;
}) {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canCreate = granted.has(FAIR_STAND_ITEMS_CREATE);
  const [form, setForm] = React.useState<CreateForm>({ ...emptyCreate });
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [fieldOptions, setFieldOptions] =
    React.useState<FairStandAdminItemFieldOptions>(EMPTY_FIELD_OPTIONS);

  React.useEffect(() => {
    void listFairStandAdminItemRecords({ page: 1, pageSize: 1 })
      .then((response) => {
        if (response.filterOptions) {
          setFieldOptions(response.filterOptions);
        }
      })
      .catch(() => {
        /* ignore */
      });
  }, []);

  const saveCreate = async () => {
    if (!canCreate) return;
    setSaving(true);
    setError(null);
    try {
      const record = await createFairStandAdminItemRecord({
        item_key: requireText(form.item_key, adminLabels.fairStandItemsFieldItemKey),
        name: requireText(form.name, adminLabels.fairStandItemsFieldName),
        item_type: requireText(form.item_type, adminLabels.fairStandItemsFieldItemType),
      });
      onCreated(record.itemKey);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandItemsSaveError);
    } finally {
      setSaving(false);
    }
  };

  if (!canCreate) {
    return (
      <PageShell>
        <PageHeader title={adminLabels.fairStandItemsCreateTitle} />
        <Banner variant="info">{adminLabels.fairStandItemsPermissionDenied}</Banner>
        <Button variant="secondary" onClick={onCancel}>
          {adminLabels.fairStandItemsBackToList}
        </Button>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <FormDirtyHost onClose={onCancel}>
        <ItemCreateView
          form={form}
          fieldOptions={fieldOptions}
          saving={saving}
          banners={error ? <Banner variant="error">{error}</Banner> : null}
          onChange={setForm}
          onSubmit={() => {
            void saveCreate();
          }}
        />
      </FormDirtyHost>
    </PageShell>
  );
}

function ItemsDetailPage({
  itemKey,
  onBack,
  onEdit,
}: {
  itemKey: string;
  onBack: () => void;
  onEdit: (itemKey: string) => void;
}) {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canUpdate = granted.has(FAIR_STAND_ITEMS_UPDATE);
  const canArchive = granted.has(FAIR_STAND_ITEMS_ARCHIVE);
  const [detail, setDetail] = React.useState<FairStandAdminItemRecord | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(() => takeItemsFlash());
  const [archiveTargetKey, setArchiveTargetKey] = React.useState<string | null>(null);

  const loadDetail = React.useCallback(async () => {
    setLoading(true);
    try {
      setDetail(await getFairStandAdminItemRecord(itemKey));
      setError(null);
    } catch (detailError) {
      setDetail(null);
      setError(
        detailError instanceof Error ? detailError.message : adminLabels.fairStandItemsDetailLoadError,
      );
    } finally {
      setLoading(false);
    }
  }, [itemKey]);

  React.useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const handleArchive = async () => {
    try {
      await archiveFairStandAdminItemRecord(itemKey);
      setArchiveTargetKey(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      await loadDetail();
    } catch (archiveError) {
      setArchiveTargetKey(null);
      setSuccess(null);
      setError(
        archiveError instanceof Error ? archiveError.message : adminLabels.fairStandItemsArchiveError,
      );
    }
  };

  const handleRestore = async () => {
    try {
      await restoreFairStandAdminItemRecord(itemKey);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      setError(null);
      await loadDetail();
    } catch (restoreError) {
      setSuccess(null);
      setError(
        restoreError instanceof Error ? restoreError.message : adminLabels.fairStandItemsRestoreError,
      );
    }
  };

  const banners = (
    <>
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
    </>
  );

  if (loading) {
    return (
      <PageShell>
        <LoadingState />
      </PageShell>
    );
  }

  if (!detail) {
    return (
      <PageShell>
        <PageHeader
          title={itemKey}
          breadcrumbs={[
            { label: adminLabels.fairStandItemsBackToList, onClick: onBack },
            { label: itemKey, current: true },
          ]}
        />
        {banners}
        <Button variant="secondary" onClick={onBack}>
          {adminLabels.fairStandItemsBackToList}
        </Button>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <ItemDetailView
        detail={detail}
        banners={banners}
        canUpdate={canUpdate}
        canArchive={canArchive}
        onBack={onBack}
        onEdit={() => onEdit(detail.itemKey)}
        onArchive={() => setArchiveTargetKey(detail.itemKey)}
        onRestore={() => {
          void handleRestore();
        }}
      />
      {archiveTargetKey ? (
        <ConfirmDialog
          title={adminLabels.fairStandItemsArchiveConfirmTitle}
          message={adminLabels.fairStandItemsArchiveConfirmMessage}
          confirmLabel={adminLabels.fairStandItemsArchiveConfirm}
          cancelLabel={adminLabels.fairStandItemsCancel}
          onCancel={() => setArchiveTargetKey(null)}
          onConfirm={() => {
            void handleArchive();
          }}
        />
      ) : null}
    </PageShell>
  );
}

function ItemsEditPage({
  itemKey,
  onCancel,
  onSaved,
}: {
  itemKey: string;
  onCancel: (itemKey: string) => void;
  onSaved: (itemKey: string) => void;
}) {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canUpdate = granted.has(FAIR_STAND_ITEMS_UPDATE);
  const [form, setForm] = React.useState<EditForm | null>(null);
  const [baseline, setBaseline] = React.useState<EditForm | null>(null);
  const [title, setTitle] = React.useState(itemKey);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [fieldOptions, setFieldOptions] =
    React.useState<FairStandAdminItemFieldOptions>(EMPTY_FIELD_OPTIONS);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void Promise.all([
      getFairStandAdminItemRecord(itemKey),
      listFairStandAdminItemRecords({ page: 1, pageSize: 1 }).catch(() => null),
    ])
      .then(([record, listResponse]) => {
        if (cancelled) return;
        const next = detailToForm(record);
        setForm(next);
        setBaseline(next);
        setTitle(record.name);
        if (listResponse?.filterOptions) {
          setFieldOptions(listResponse.filterOptions);
        }
        setError(null);
      })
      .catch((loadError: unknown) => {
        if (cancelled) return;
        setForm(null);
        setBaseline(null);
        setError(
          loadError instanceof Error ? loadError.message : adminLabels.fairStandItemsDetailLoadError,
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [itemKey]);

  const saveEdit = async () => {
    if (!canUpdate || !form) return;
    setSaving(true);
    setError(null);
    try {
      await updateFairStandAdminItemRecord(itemKey, buildUpdatePayload(form));
      onSaved(itemKey);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandItemsSaveError);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageShell>
        <LoadingState />
      </PageShell>
    );
  }

  if (!canUpdate) {
    return (
      <PageShell>
        <PageHeader title={adminLabels.fairStandItemsEditTitle} />
        <Banner variant="info">{adminLabels.fairStandItemsPermissionDenied}</Banner>
        <Button variant="secondary" onClick={() => onCancel(itemKey)}>
          {adminLabels.fairStandItemsBack}
        </Button>
      </PageShell>
    );
  }

  if (!form || !baseline) {
    return (
      <PageShell>
        <PageHeader
          title={adminLabels.fairStandItemsEditTitle}
          breadcrumbs={[
            { label: title, onClick: () => onCancel(itemKey) },
            { label: adminLabels.fairStandItemsEditTitle, current: true },
          ]}
        />
        {error ? <Banner variant="error">{error}</Banner> : null}
        <Button variant="secondary" onClick={() => onCancel(itemKey)}>
          {adminLabels.fairStandItemsBack}
        </Button>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <FormDirtyHost onClose={() => onCancel(itemKey)}>
        <ItemEditView
          itemKey={itemKey}
          title={title}
          form={form}
          baseline={baseline}
          fieldOptions={fieldOptions}
          saving={saving}
          banners={error ? <Banner variant="error">{error}</Banner> : null}
          onChange={setForm}
          onSubmit={() => {
            void saveEdit();
          }}
        />
      </FormDirtyHost>
    </PageShell>
  );
}

const componentColumns: UniversalDataTableColumn<FairStandAdminItemComponent>[] = [
  {
    key: "childItemKey",
    title: adminLabels.fairStandItemsFieldChildItemKey,
    sortable: false,
    render: (row) => row.childItemKey,
  },
  {
    key: "childName",
    title: adminLabels.fairStandItemsColItemName,
    sortable: false,
    render: (row) => row.childName ?? "—",
  },
  {
    key: "childType",
    title: adminLabels.fairStandItemsColType,
    sortable: false,
    render: (row) => row.childType ?? "—",
  },
  {
    key: "quantity",
    title: adminLabels.fairStandItemsFieldQuantity,
    sortable: false,
    render: (row) => String(row.quantity),
  },
];

const bodyPartColumns: UniversalDataTableColumn<FairStandAdminItemBodyPart>[] = [
  {
    key: "childItemKey",
    title: adminLabels.fairStandItemsFieldChildItemKey,
    sortable: false,
    render: (row) => row.childItemKey,
  },
  {
    key: "childName",
    title: adminLabels.fairStandItemsColItemName,
    sortable: false,
    render: (row) => row.childName ?? "—",
  },
  {
    key: "childType",
    title: adminLabels.fairStandItemsColType,
    sortable: false,
    render: (row) => row.childType ?? "—",
  },
  {
    key: "bodyRole",
    title: adminLabels.fairStandItemsFieldBodyRole,
    sortable: false,
    render: (row) => row.bodyRole,
  },
];

const assetColumns: UniversalDataTableColumn<FairStandAdminItemAsset>[] = [
  {
    key: "assetRole",
    title: adminLabels.fairStandItemsFieldAssetRole,
    sortable: false,
    render: (row) => row.assetRole,
  },
  {
    key: "relativePath",
    title: adminLabels.fairStandItemsFieldRelativePath,
    sortable: false,
    render: (row) => row.relativePath,
  },
  {
    key: "isActive",
    title: adminLabels.fairStandItemsFieldAssetActive,
    sortable: false,
    render: (row) => (
      <Badge variant={row.isActive ? "success" : "neutral"}>
        {row.isActive ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo}
      </Badge>
    ),
  },
];

function ItemDetailView({
  detail,
  banners,
  canUpdate,
  canArchive,
  onBack,
  onEdit,
  onArchive,
  onRestore,
}: {
  detail: FairStandAdminItemRecord;
  banners: React.ReactNode;
  canUpdate: boolean;
  canArchive: boolean;
  onBack: () => void;
  onEdit: () => void;
  onArchive: () => void;
  onRestore: () => void;
}) {
  const [activeTab, setActiveTab] = React.useState<DetailTabId>("general");
  const [categories, setCategories] = React.useState<FairStandAdminCategory[]>([]);
  const [previews, setPreviews] = React.useState<FairStandAdminPreview[]>([]);
  const dims = detail.dimensions;
  const scene = detail.sceneDimensions;
  const strip = detail.stripOccupancy;
  const video = detail.videoWall;
  const componentCount = detail.components.length + detail.bodyParts.length;
  const assetCount = detail.assets.length;

  React.useEffect(() => {
    let cancelled = false;
    void Promise.all([
      listFairStandAdminCategories().catch(() => [] as FairStandAdminCategory[]),
      listFairStandAdminPreviews().catch(() => [] as FairStandAdminPreview[]),
    ]).then(([nextCategories, nextPreviews]) => {
      if (cancelled) return;
      setCategories(nextCategories);
      setPreviews(nextPreviews);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const categoryLabel =
    detail.categoryId == null
      ? "—"
      : (categories.find((category) => category.id === detail.categoryId)?.catalogName ??
        String(detail.categoryId));
  const selectedPreview =
    detail.previewId == null
      ? null
      : (previews.find((preview) => preview.id === detail.previewId) ?? null);

  const actions: PageHeaderAction[] = [];
  if (canUpdate) {
    actions.push({
      id: "edit",
      label: adminLabels.fairStandItemsActionEdit,
      onClick: onEdit,
      variant: "primary",
    });
  }
  if (canArchive && detail.isActive) {
    actions.push({
      id: "archive",
      label: adminLabels.fairStandItemsActionArchive,
      onClick: onArchive,
      variant: "danger",
    });
  }
  if (canArchive && !detail.isActive) {
    actions.push({
      id: "restore",
      label: adminLabels.fairStandItemsActionRestore,
      onClick: onRestore,
      variant: "secondary",
    });
  }

  const tabItems = [
    { id: "general" as const, label: adminLabels.fairStandItemsTabGeneral },
    { id: "dimensions" as const, label: adminLabels.fairStandItemsTabDimensions },
    {
      id: "components" as const,
      label: adminLabels.fairStandItemsTabComponents,
      badge: componentCount > 0 ? componentCount : undefined,
    },
    {
      id: "assets" as const,
      label: adminLabels.fairStandItemsTabAssets,
      badge: assetCount > 0 ? assetCount : undefined,
    },
  ];

  return (
    <>
      <PageHeader
        title={detail.name}
        subtitle={
          <>
            <Badge variant="neutral">{detail.itemKey}</Badge>
            {" · "}
            <Badge variant="neutral">{detail.type}</Badge>
            {" · "}
            <Badge variant={detail.isActive ? "success" : "neutral"}>
              {detail.isActive
                ? adminLabels.fairStandItemsBadgeActive
                : adminLabels.fairStandItemsBadgeInactive}
            </Badge>
            {detail.catalogVisible ? (
              <>
                {" · "}
                <Badge variant="success">{adminLabels.fairStandItemsBadgeCatalog}</Badge>
              </>
            ) : null}
            {detail.isRender ? (
              <>
                {" · "}
                <Badge variant="success">{adminLabels.fairStandItemsBadgeRender}</Badge>
              </>
            ) : null}
          </>
        }
        breadcrumbs={[
          { label: adminLabels.fairStandItemsBackToList, onClick: onBack },
          { label: detail.name, current: true },
        ]}
        actions={actions}
      />
      {banners}

      <Tabs items={tabItems} active={activeTab} onChange={setActiveTab} />

      <TabPanel id="panel-general" labelledBy="tab-general" active={activeTab === "general"}>
        <Card>
          <dl className="detail-grid">
            <DetailItem
              label={adminLabels.fairStandItemsFieldItemKey}
              hint={adminLabels.fairStandItemsFieldItemKeyHint}
            >
              {detail.itemKey}
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldName}
              hint={adminLabels.fairStandItemsFieldNameHint}
            >
              {detail.name}
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldItemType}
              hint={adminLabels.fairStandItemsFieldItemTypeHint}
            >
              {detail.type}
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldUnit}
              hint={adminLabels.fairStandItemsFieldUnitHint}
            >
              <DetailValue value={detail.unit} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldMaterial}
              hint={adminLabels.fairStandItemsFieldMaterialHint}
            >
              <DetailValue value={detail.material} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldShape}
              hint={adminLabels.fairStandItemsFieldShapeHint}
            >
              <DetailValue value={detail.shape} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldVariant}
              hint={adminLabels.fairStandItemsFieldVariantHint}
            >
              <DetailValue value={detail.variant} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldCompositionMode}
              hint={adminLabels.fairStandItemsFieldCompositionModeHint}
            >
              <DetailValue value={detail.compositionMode} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldCatalogVisible}
              hint={adminLabels.fairStandItemsFieldCatalogVisibleHint}
            >
              <YesNoBadge value={detail.catalogVisible} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldCategoryId}
              hint={adminLabels.fairStandItemsFieldCategoryIdHint}
            >
              <DetailValue value={categoryLabel} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldCatalogItemIndex}
              hint={adminLabels.fairStandItemsFieldCatalogItemIndexHint}
            >
              <DetailValue value={str(detail.catalogItemIndex)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldPreviewId}
              hint={adminLabels.fairStandItemsFieldPreviewIdHint}
            >
              {selectedPreview ? (
                <div className="fair-stand-detail-preview">
                  <span className="fair-stand-detail-preview-thumb" aria-hidden="true">
                    <FairStandCatalogLivePreview definition={selectedPreview} widthCm={60} />
                  </span>
                  <DetailValue value={selectedPreview.displayName} />
                </div>
              ) : (
                <DetailValue value={str(detail.previewId)} />
              )}
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldIsRender}
              hint={adminLabels.fairStandItemsFieldIsRenderHint}
            >
              <YesNoBadge value={detail.isRender} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldPreserveModelScale}
              hint={adminLabels.fairStandItemsFieldPreserveModelScaleHint}
            >
              <YesNoBadge value={detail.preserveModelScale} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldPaintable}
              hint={adminLabels.fairStandItemsFieldPaintableHint}
            >
              <YesNoBadge value={detail.paintable} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldAcceptsColor}
              hint={adminLabels.fairStandItemsFieldAcceptsColorHint}
            >
              <YesNoBadge value={detail.acceptsColor} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldAcceptsImage}
              hint={adminLabels.fairStandItemsFieldAcceptsImageHint}
            >
              <YesNoBadge value={detail.acceptsImage} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldAcceptsLightbox}
              hint={adminLabels.fairStandItemsFieldAcceptsLightboxHint}
            >
              <YesNoBadge value={detail.acceptsLightbox} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldAcceptsGlass}
              hint={adminLabels.fairStandItemsFieldAcceptsGlassHint}
            >
              <YesNoBadge value={detail.acceptsGlass} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldAcceptsMesh}
              hint={adminLabels.fairStandItemsFieldAcceptsMeshHint}
            >
              <YesNoBadge value={detail.acceptsMesh} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldSideInsertRotation}
              hint={adminLabels.fairStandItemsFieldSideInsertRotationHint}
            >
              <DetailValue value={detail.sideInsertRotation} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldSnapRequires}
              hint={adminLabels.fairStandItemsFieldSnapRequiresHint}
            >
              <DetailValue value={detail.snapRequires} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldSnapProvides}
              hint={adminLabels.fairStandItemsFieldSnapProvidesHint}
            >
              <DetailValue value={detail.snapProvides} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldDefaultZ}
              hint={adminLabels.fairStandItemsFieldDefaultZHint}
            >
              <DetailValue value={str(detail.defaultZCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldDefaultColor}
              hint={adminLabels.fairStandItemsFieldDefaultColorHint}
            >
              <DetailValue value={str(detail.defaultColor)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldEyeCount}
              hint={adminLabels.fairStandItemsFieldEyeCountHint}
            >
              <DetailValue value={str(detail.eyeCount)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldModelRotationY}
              hint={adminLabels.fairStandItemsFieldModelRotationYHint}
            >
              <DetailValue value={str(detail.modelRotationYDeg)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldVisualRotationY}
              hint={adminLabels.fairStandItemsFieldVisualRotationYHint}
            >
              <DetailValue value={str(detail.visualRotationYDeg)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldRotationStep}
              hint={adminLabels.fairStandItemsFieldRotationStepHint}
            >
              <DetailValue value={str(detail.rotationStepDeg)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldDefaultRotation}
              hint={adminLabels.fairStandItemsFieldDefaultRotationHint}
            >
              <DetailValue value={str(detail.defaultRotationDeg)} />
            </DetailItem>
          </dl>
        </Card>
      </TabPanel>

      <TabPanel
        id="panel-dimensions"
        labelledBy="tab-dimensions"
        active={activeTab === "dimensions"}
      >
        <Card>
          <dl className="detail-grid">
            <DetailItem
              label={adminLabels.fairStandItemsFieldWidthCm}
              hint={adminLabels.fairStandItemsFieldWidthCmHint}
            >
              <DetailValue value={str(dims?.widthCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldDepthCm}
              hint={adminLabels.fairStandItemsFieldDepthCmHint}
            >
              <DetailValue value={str(dims?.depthCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldHeightCm}
              hint={adminLabels.fairStandItemsFieldHeightCmHint}
            >
              <DetailValue value={str(dims?.heightCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldMountHeightCm}
              hint={adminLabels.fairStandItemsFieldMountHeightCmHint}
            >
              <DetailValue value={str(dims?.mountHeightCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldWallGapCm}
              hint={adminLabels.fairStandItemsFieldWallGapCmHint}
            >
              <DetailValue value={str(dims?.wallGapCm)} />
            </DetailItem>
            <DetailItem
              label={`${adminLabels.fairStandItemsSectionSceneDimensions} · ${adminLabels.fairStandItemsFieldWidthCm}`}
              hint={adminLabels.fairStandItemsFieldSceneWidthCmHint}
            >
              <DetailValue value={str(scene?.widthCm)} />
            </DetailItem>
            <DetailItem
              label={`${adminLabels.fairStandItemsSectionSceneDimensions} · ${adminLabels.fairStandItemsFieldDepthCm}`}
              hint={adminLabels.fairStandItemsFieldSceneDepthCmHint}
            >
              <DetailValue value={str(scene?.depthCm)} />
            </DetailItem>
            <DetailItem
              label={`${adminLabels.fairStandItemsSectionSceneDimensions} · ${adminLabels.fairStandItemsFieldHeightCm}`}
              hint={adminLabels.fairStandItemsFieldSceneHeightCmHint}
            >
              <DetailValue value={str(scene?.heightCm)} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldStripAlign}
              hint={adminLabels.fairStandItemsFieldStripAlignHint}
            >
              <DetailValue value={strip?.align} />
            </DetailItem>
            <DetailItem
              label={adminLabels.fairStandItemsFieldStripCount}
              hint={adminLabels.fairStandItemsFieldStripCountHint}
            >
              <DetailValue value={str(strip?.stripCount)} />
            </DetailItem>
            {video ? (
              <>
                <DetailItem
                  label={adminLabels.fairStandItemsFieldVideoRows}
                  hint={adminLabels.fairStandItemsFieldVideoRowsHint}
                >
                  <DetailValue value={str(video.rows)} />
                </DetailItem>
                <DetailItem
                  label={adminLabels.fairStandItemsFieldVideoCols}
                  hint={adminLabels.fairStandItemsFieldVideoColsHint}
                >
                  <DetailValue value={str(video.cols)} />
                </DetailItem>
                <DetailItem
                  label={adminLabels.fairStandItemsFieldPanelItemKey}
                  hint={adminLabels.fairStandItemsFieldPanelItemKeyHint}
                >
                  <DetailValue value={video.panelItemKey} />
                </DetailItem>
              </>
            ) : null}
          </dl>
        </Card>
      </TabPanel>

      <TabPanel
        id="panel-components"
        labelledBy="tab-components"
        active={activeTab === "components"}
      >
        <p className="field-hint">{adminLabels.fairStandItemsComponentsDescription}</p>
        <UniversalDataTable
          items={detail.components}
          columns={componentColumns}
          rowKey={(row) => row.id}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyComponents} />}
        />
        <p className="field-hint">{adminLabels.fairStandItemsBodyPartsDescription}</p>
        <UniversalDataTable
          items={detail.bodyParts}
          columns={bodyPartColumns}
          rowKey={(row) => `${row.bodyRole}-${row.childItemKey}`}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyBodyParts} />}
        />
      </TabPanel>

      <TabPanel id="panel-assets" labelledBy="tab-assets" active={activeTab === "assets"}>
        <p className="field-hint">{adminLabels.fairStandItemsAssetsDescription}</p>
        <UniversalDataTable
          items={detail.assets}
          columns={assetColumns}
          rowKey={(row) => row.id}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyAssets} />}
        />
      </TabPanel>
    </>
  );
}

function ItemCreateView({
  form,
  fieldOptions,
  saving,
  banners,
  onChange,
  onSubmit,
}: {
  form: CreateForm;
  fieldOptions: FairStandAdminItemFieldOptions;
  saving: boolean;
  banners: React.ReactNode;
  onChange: (form: CreateForm) => void;
  onSubmit: () => void;
}) {
  const requestBack = useFormDirtyCancel(() => undefined);
  const [itemKeyManual, setItemKeyManual] = React.useState(false);
  return (
    <>
      <FormDirtyReporter values={form} baseline={emptyCreate} />
      <PageHeader
        title={adminLabels.fairStandItemsCreateTitle}
        subtitle={adminLabels.fairStandItemsSubtitle}
        breadcrumbs={[
          { label: adminLabels.fairStandItemsBackToList, onClick: requestBack },
          { label: adminLabels.fairStandItemsCreateTitle, current: true },
        ]}
      />
      {banners}
      <form
        className="crm-form crm-form--narrow"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <FormSection title={adminLabels.fairStandItemsSectionIdentity}>
          <FormGrid>
            <FormField
              label={adminLabels.fairStandItemsFieldName}
              htmlFor="fs-item-name"
              hint={adminLabels.fairStandItemsFieldNameHint}
              required
              fullWidth
            >
              <TextInput
                id="fs-item-name"
                value={form.name}
                disabled={saving}
                onChange={(event) => {
                  const name = event.target.value;
                  onChange({
                    ...form,
                    name,
                    item_key: itemKeyManual ? form.item_key : slugifyItemKey(name),
                  });
                }}
                required
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldItemKey}
              htmlFor="fs-item-key"
              hint={adminLabels.fairStandItemsFieldItemKeyHint}
              required
              fullWidth
            >
              <TextInput
                id="fs-item-key"
                value={form.item_key}
                disabled={saving}
                onChange={(event) => {
                  setItemKeyManual(true);
                  onChange({ ...form, item_key: event.target.value });
                }}
                required
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldItemType}
              htmlFor="fs-item-type"
              hint={adminLabels.fairStandItemsFieldItemTypeHint}
              required
              fullWidth
            >
              <SelectInput
                id="fs-item-type"
                value={form.item_type}
                disabled={saving}
                required
                onChange={(event) => onChange({ ...form, item_type: event.target.value })}
              >
                {itemTypeSelectOptions(fieldOptions.itemTypes, form.item_type)}
              </SelectInput>
            </FormField>
          </FormGrid>
        </FormSection>

        <FormActions
          onCancel={requestBack}
          cancelLabel={adminLabels.fairStandItemsCancel}
          submitLabel={adminLabels.fairStandItemsSave}
          saving={saving}
        />
      </form>
    </>
  );
}

function ItemEditView({
  itemKey,
  title,
  form,
  baseline,
  fieldOptions,
  saving,
  banners,
  onChange,
  onSubmit,
}: {
  itemKey: string;
  title: string;
  form: EditForm;
  baseline: EditForm;
  fieldOptions: FairStandAdminItemFieldOptions;
  saving: boolean;
  banners: React.ReactNode;
  onChange: (form: EditForm) => void;
  onSubmit: () => void;
}) {
  const requestBack = useFormDirtyCancel(() => undefined);
  const [activeTab, setActiveTab] = React.useState<DetailTabId>("general");
  const [removeTarget, setRemoveTarget] = React.useState<
    { kind: "component" | "bodyPart"; index: number } | null
  >(null);
  const [componentDraft, setComponentDraft] = React.useState({
    child_item_key: "",
    quantity: "1",
  });
  const [bodyDraft, setBodyDraft] = React.useState({
    child_item_key: "",
    body_role: "",
  });
  const [addingComponent, setAddingComponent] = React.useState(false);
  const [addingBodyPart, setAddingBodyPart] = React.useState(false);
  const [categories, setCategories] = React.useState<FairStandAdminCategory[]>([]);
  const [previews, setPreviews] = React.useState<FairStandAdminPreview[]>([]);
  const unitListId = "fs-edit-unit-options";
  const materialListId = "fs-edit-material-options";
  const shapeListId = "fs-edit-shape-options";
  const variantListId = "fs-edit-variant-options";
  const compositionModeListId = "fs-edit-comp-mode-options";
  const sideInsertListId = "fs-edit-side-insert-options";
  const componentCount = form.components.length + form.body_parts.length;
  const assetCount = form.assets.length;
  const formRef = React.useRef(form);
  formRef.current = form;

  React.useEffect(() => {
    let cancelled = false;
    void Promise.all([
      listFairStandAdminCategories().catch(() => [] as FairStandAdminCategory[]),
      listFairStandAdminPreviews().catch(() => [] as FairStandAdminPreview[]),
    ]).then(([nextCategories, nextPreviews]) => {
      if (cancelled) return;
      setCategories(nextCategories);
      setPreviews(nextPreviews);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedCategoryId = form.category_id.trim() ? Number(form.category_id) : null;
  const categoryOptions = React.useMemo(
    () =>
      categories.filter(
        (category) => category.isActive || category.id === selectedCategoryId,
      ),
    [categories, selectedCategoryId],
  );

  const patch = <K extends keyof EditForm>(key: K, value: EditForm[K]) =>
    onChange({ ...form, [key]: value });

  const resolveChildMeta = React.useCallback(async (itemKey: string) => {
    const key = itemKey.trim();
    if (!key) return { child_name: "", child_type: "" };
    try {
      const record = await getFairStandAdminItemRecord(key);
      return { child_name: record.name, child_type: record.type };
    } catch {
      return { child_name: "", child_type: "" };
    }
  }, []);

  const addComponentFromDraft = async () => {
    const childKey = componentDraft.child_item_key.trim();
    if (!childKey) return;
    setAddingComponent(true);
    try {
      const meta = await resolveChildMeta(childKey);
      const current = formRef.current;
      onChange({
        ...current,
        components: [
          ...current.components,
          {
            child_item_key: childKey,
            child_name: meta.child_name,
            child_type: meta.child_type,
            quantity: componentDraft.quantity.trim() || "1",
          },
        ],
      });
      setComponentDraft({
        child_item_key: "",
        quantity: "1",
      });
    } finally {
      setAddingComponent(false);
    }
  };

  const addBodyPartFromDraft = async () => {
    const childKey = bodyDraft.child_item_key.trim();
    const bodyRole = bodyDraft.body_role.trim();
    if (!childKey || !bodyRole) return;
    setAddingBodyPart(true);
    try {
      const meta = await resolveChildMeta(childKey);
      const current = formRef.current;
      onChange({
        ...current,
        body_parts: [
          ...current.body_parts,
          {
            body_role: bodyRole,
            child_item_key: childKey,
            child_name: meta.child_name,
            child_type: meta.child_type,
          },
        ],
      });
      setBodyDraft({ child_item_key: "", body_role: "" });
    } finally {
      setAddingBodyPart(false);
    }
  };

  const editComponentColumns: UniversalDataTableColumn<ComponentFormRow & { index: number }>[] =
    React.useMemo(
      () => [
        {
          key: "child_item_key",
          title: adminLabels.fairStandItemsFieldChildItemKey,
          sortable: false,
          render: (row) => row.child_item_key.trim() || "—",
        },
        {
          key: "child_name",
          title: adminLabels.fairStandItemsColItemName,
          sortable: false,
          render: (row) => row.child_name.trim() || "—",
        },
        {
          key: "child_type",
          title: adminLabels.fairStandItemsColType,
          sortable: false,
          render: (row) => row.child_type.trim() || "—",
        },
        {
          key: "quantity",
          title: adminLabels.fairStandItemsFieldQuantity,
          sortable: false,
          render: (row) => (
            <TextInput
              type="number"
              value={row.quantity}
              disabled={saving}
              aria-label={adminLabels.fairStandItemsFieldQuantity}
              onChange={(event) => {
                const components = [...form.components];
                components[row.index] = {
                  ...components[row.index],
                  quantity: event.target.value,
                };
                onChange({ ...form, components });
              }}
            />
          ),
        },
        {
          key: "actions",
          title: adminLabels.fairStandItemsColActions,
          sortable: false,
          render: (row) => (
            <TableRowActions>
              <button
                type="button"
                className="btn link danger"
                disabled={saving}
                onClick={() => setRemoveTarget({ kind: "component", index: row.index })}
              >
                {adminLabels.fairStandItemsRemoveComponent}
              </button>
            </TableRowActions>
          ),
        },
      ],
      [form, onChange, saving],
    );

  const editBodyPartColumns: UniversalDataTableColumn<BodyPartFormRow & { index: number }>[] =
    React.useMemo(
      () => [
        {
          key: "child_item_key",
          title: adminLabels.fairStandItemsFieldChildItemKey,
          sortable: false,
          render: (row) => row.child_item_key.trim() || "—",
        },
        {
          key: "child_name",
          title: adminLabels.fairStandItemsColItemName,
          sortable: false,
          render: (row) => row.child_name.trim() || "—",
        },
        {
          key: "child_type",
          title: adminLabels.fairStandItemsColType,
          sortable: false,
          render: (row) => row.child_type.trim() || "—",
        },
        {
          key: "body_role",
          title: adminLabels.fairStandItemsFieldBodyRole,
          sortable: false,
          render: (row) => row.body_role.trim() || "—",
        },
        {
          key: "actions",
          title: adminLabels.fairStandItemsColActions,
          sortable: false,
          render: (row) => (
            <TableRowActions>
              <button
                type="button"
                className="btn link danger"
                disabled={saving}
                onClick={() => setRemoveTarget({ kind: "bodyPart", index: row.index })}
              >
                {adminLabels.fairStandItemsRemoveBodyPart}
              </button>
            </TableRowActions>
          ),
        },
      ],
      [saving],
    );

  const dimensionFields: [keyof EditForm, string, string][] = [
    ["width_cm", adminLabels.fairStandItemsFieldWidthCm, adminLabels.fairStandItemsFieldWidthCmHint],
    ["depth_cm", adminLabels.fairStandItemsFieldDepthCm, adminLabels.fairStandItemsFieldDepthCmHint],
    ["height_cm", adminLabels.fairStandItemsFieldHeightCm, adminLabels.fairStandItemsFieldHeightCmHint],
    [
      "mount_height_cm",
      adminLabels.fairStandItemsFieldMountHeightCm,
      adminLabels.fairStandItemsFieldMountHeightCmHint,
    ],
    ["wall_gap_cm", adminLabels.fairStandItemsFieldWallGapCm, adminLabels.fairStandItemsFieldWallGapCmHint],
  ];

  const tabItems = [
    { id: "general" as const, label: adminLabels.fairStandItemsTabGeneral },
    { id: "dimensions" as const, label: adminLabels.fairStandItemsTabDimensions },
    {
      id: "components" as const,
      label: adminLabels.fairStandItemsTabComponents,
      badge: componentCount > 0 ? componentCount : undefined,
    },
    {
      id: "assets" as const,
      label: adminLabels.fairStandItemsTabAssets,
      badge: assetCount > 0 ? assetCount : undefined,
    },
  ];

  return (
    <>
      <FormDirtyReporter values={form} baseline={baseline} />
      <PageHeader
        title={form.name.trim() || title}
        subtitle={
          <>
            <Badge variant="neutral">{itemKey}</Badge>
            {" · "}
            <Badge variant="neutral">
              {form.item_type.trim() || adminLabels.fairStandItemsEditTitle}
            </Badge>
            {" · "}
            {adminLabels.fairStandItemsEditTitle}
          </>
        }
        breadcrumbs={[
          { label: title, onClick: requestBack },
          { label: adminLabels.fairStandItemsEditTitle, current: true },
        ]}
      />
      {banners}
      <form
        className="crm-form crm-form--wide"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <Tabs items={tabItems} active={activeTab} onChange={setActiveTab} />

        <TabPanel id="panel-edit-general" labelledBy="tab-general" active={activeTab === "general"}>
          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionIdentity}</h3>
            <FormField
              label={adminLabels.fairStandItemsFieldItemKey}
              htmlFor="fs-edit-item-key"
              hint={adminLabels.fairStandItemsFieldItemKeyHint}
            >
              <TextInput id="fs-edit-item-key" value={itemKey} readOnly disabled />
            </FormField>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldName}
                htmlFor="fs-edit-name"
                hint={adminLabels.fairStandItemsFieldNameHint}
                required
              >
                <TextInput
                  id="fs-edit-name"
                  value={form.name}
                  disabled={saving}
                  onChange={(event) => patch("name", event.target.value)}
                  required
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldItemType}
                htmlFor="fs-edit-type"
                hint={adminLabels.fairStandItemsFieldItemTypeHint}
                required
              >
                <SelectInput
                  id="fs-edit-type"
                  value={form.item_type}
                  disabled={saving}
                  required
                  onChange={(event) => patch("item_type", event.target.value)}
                >
                  {itemTypeSelectOptions(fieldOptions.itemTypes, form.item_type)}
                </SelectInput>
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldUnit}
                htmlFor="fs-edit-unit"
                hint={adminLabels.fairStandItemsFieldUnitHint}
              >
                <SuggestTextInput
                  id="fs-edit-unit"
                  listId={unitListId}
                  options={fieldOptions.units}
                  value={form.unit}
                  disabled={saving}
                  onChange={(unit) => patch("unit", unit)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldMaterial}
                htmlFor="fs-edit-material"
                hint={adminLabels.fairStandItemsFieldMaterialHint}
              >
                <SuggestTextInput
                  id="fs-edit-material"
                  listId={materialListId}
                  options={fieldOptions.materials}
                  value={form.material}
                  disabled={saving}
                  onChange={(material) => patch("material", material)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldShape}
                htmlFor="fs-edit-shape"
                hint={adminLabels.fairStandItemsFieldShapeHint}
              >
                <SuggestTextInput
                  id="fs-edit-shape"
                  listId={shapeListId}
                  options={fieldOptions.shapes}
                  value={form.shape}
                  disabled={saving}
                  onChange={(shape) => patch("shape", shape)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldVariant}
                htmlFor="fs-edit-variant"
                hint={adminLabels.fairStandItemsFieldVariantHint}
              >
                <SuggestTextInput
                  id="fs-edit-variant"
                  listId={variantListId}
                  options={fieldOptions.variants}
                  value={form.variant}
                  disabled={saving}
                  onChange={(variant) => patch("variant", variant)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldCompositionMode}
                htmlFor="fs-edit-comp-mode"
                hint={adminLabels.fairStandItemsFieldCompositionModeHint}
              >
                <SuggestTextInput
                  id="fs-edit-comp-mode"
                  listId={compositionModeListId}
                  options={fieldOptions.compositionModes}
                  value={form.composition_mode}
                  disabled={saving}
                  onChange={(composition_mode) => patch("composition_mode", composition_mode)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldDefaultColor}
                htmlFor="fs-edit-default-color"
                hint={adminLabels.fairStandItemsFieldDefaultColorHint}
              >
                <TextInput
                  id="fs-edit-default-color"
                  type="number"
                  value={form.default_color}
                  disabled={saving}
                  onChange={(event) => patch("default_color", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldEyeCount}
                htmlFor="fs-edit-eye-count"
                hint={adminLabels.fairStandItemsFieldEyeCountHint}
              >
                <TextInput
                  id="fs-edit-eye-count"
                  type="number"
                  value={form.eye_count}
                  disabled={saving}
                  onChange={(event) => patch("eye_count", event.target.value)}
                />
              </FormField>
            </FormGrid>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionCatalog}</h3>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldCategoryId}
                htmlFor="fs-edit-category"
                hint={adminLabels.fairStandItemsFieldCategoryIdHint}
              >
                <SelectInput
                  id="fs-edit-category"
                  value={form.category_id}
                  disabled={saving}
                  onChange={(event) => patch("category_id", event.target.value)}
                >
                  <option value="">{adminLabels.fairStandCatalogSelectPlaceholder}</option>
                  {categoryOptions.map((category) => (
                    <option key={category.id} value={String(category.id)}>
                      {category.catalogName}
                    </option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldCatalogItemIndex}
                htmlFor="fs-edit-index"
                hint={adminLabels.fairStandItemsFieldCatalogItemIndexHint}
              >
                <TextInput
                  id="fs-edit-index"
                  type="number"
                  value={form.catalog_item_index}
                  disabled={saving}
                  onChange={(event) => patch("catalog_item_index", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldPreviewId}
                htmlFor="fs-edit-preview"
                hint={adminLabels.fairStandItemsFieldPreviewIdHint}
                fullWidth
              >
                <FairStandCatalogPreviewSelect
                  id="fs-edit-preview"
                  value={form.preview_id}
                  previews={previews}
                  disabled={saving}
                  onChange={(previewId) => patch("preview_id", previewId)}
                />
              </FormField>
            </FormGrid>
            <CheckboxField
              id="fs-edit-catalog-visible"
              label={adminLabels.fairStandItemsFieldCatalogVisible}
              hint={adminLabels.fairStandItemsFieldCatalogVisibleHint}
              checked={form.catalog_visible}
              disabled={saving}
              onChange={(checked) => patch("catalog_visible", checked)}
            />
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionFlags}</h3>
            <FormGrid columns={2}>
              <CheckboxField
                id="fs-edit-is-active"
                label={adminLabels.fairStandItemsFieldIsActive}
                hint={adminLabels.fairStandItemsFieldIsActiveHint}
                checked={form.is_active}
                disabled={saving}
                onChange={(checked) => patch("is_active", checked)}
              />
              <CheckboxField
                id="fs-edit-is-render"
                label={adminLabels.fairStandItemsFieldIsRender}
                hint={adminLabels.fairStandItemsFieldIsRenderHint}
                checked={form.is_render}
                disabled={saving}
                onChange={(checked) => patch("is_render", checked)}
              />
              <CheckboxField
                id="fs-edit-preserve-scale"
                label={adminLabels.fairStandItemsFieldPreserveModelScale}
                hint={adminLabels.fairStandItemsFieldPreserveModelScaleHint}
                checked={form.preserve_model_scale}
                disabled={saving}
                onChange={(checked) => patch("preserve_model_scale", checked)}
              />
              <CheckboxField
                id="fs-edit-paintable"
                label={adminLabels.fairStandItemsFieldPaintable}
                hint={adminLabels.fairStandItemsFieldPaintableHint}
                checked={form.paintable}
                disabled={saving}
                onChange={(checked) => patch("paintable", checked)}
              />
              <CheckboxField
                id="fs-edit-accepts-color"
                label={adminLabels.fairStandItemsFieldAcceptsColor}
                hint={adminLabels.fairStandItemsFieldAcceptsColorHint}
                checked={form.accepts_color}
                disabled={saving}
                onChange={(checked) => patch("accepts_color", checked)}
              />
              <CheckboxField
                id="fs-edit-accepts-image"
                label={adminLabels.fairStandItemsFieldAcceptsImage}
                hint={adminLabels.fairStandItemsFieldAcceptsImageHint}
                checked={form.accepts_image}
                disabled={saving}
                onChange={(checked) => patch("accepts_image", checked)}
              />
              <CheckboxField
                id="fs-edit-accepts-lightbox"
                label={adminLabels.fairStandItemsFieldAcceptsLightbox}
                hint={adminLabels.fairStandItemsFieldAcceptsLightboxHint}
                checked={form.accepts_lightbox}
                disabled={saving}
                onChange={(checked) => patch("accepts_lightbox", checked)}
              />
              <CheckboxField
                id="fs-edit-accepts-glass"
                label={adminLabels.fairStandItemsFieldAcceptsGlass}
                hint={adminLabels.fairStandItemsFieldAcceptsGlassHint}
                checked={form.accepts_glass}
                disabled={saving}
                onChange={(checked) => patch("accepts_glass", checked)}
              />
              <CheckboxField
                id="fs-edit-accepts-mesh"
                label={adminLabels.fairStandItemsFieldAcceptsMesh}
                hint={adminLabels.fairStandItemsFieldAcceptsMeshHint}
                checked={form.accepts_mesh}
                disabled={saving}
                onChange={(checked) => patch("accepts_mesh", checked)}
              />
            </FormGrid>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionRotation}</h3>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldDefaultZ}
                htmlFor="fs-edit-default-z"
                hint={adminLabels.fairStandItemsFieldDefaultZHint}
              >
                <TextInput
                  id="fs-edit-default-z"
                  type="number"
                  value={form.default_z_cm}
                  disabled={saving}
                  onChange={(event) => patch("default_z_cm", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldSnapRequires}
                htmlFor="fs-edit-snap-requires"
                hint={adminLabels.fairStandItemsFieldSnapRequiresHint}
              >
                <SelectInput
                  id="fs-edit-snap-requires"
                  value={form.snap_requires_rule_id}
                  disabled={saving || Boolean(form.snap_provides_rule_id.trim())}
                  onChange={(event) => patch("snap_requires_rule_id", event.target.value)}
                >
                  <option value="">{adminLabels.fairStandCatalogSelectPlaceholder}</option>
                  {fieldOptions.snapRules.map((rule) => (
                    <option key={rule.id} value={String(rule.id)}>
                      {rule.displayName} ({rule.key}
                      {rule.face || rule.edge ? ` · ${rule.face ?? "—"}/${rule.edge ?? "—"}` : ""})
                    </option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldSnapProvides}
                htmlFor="fs-edit-snap-provides"
                hint={adminLabels.fairStandItemsFieldSnapProvidesHint}
              >
                <SelectInput
                  id="fs-edit-snap-provides"
                  value={form.snap_provides_rule_id}
                  disabled={saving || Boolean(form.snap_requires_rule_id.trim())}
                  onChange={(event) => patch("snap_provides_rule_id", event.target.value)}
                >
                  <option value="">{adminLabels.fairStandCatalogSelectPlaceholder}</option>
                  {fieldOptions.snapRules.map((rule) => (
                    <option key={rule.id} value={String(rule.id)}>
                      {rule.displayName} ({rule.key}
                      {rule.face || rule.edge ? ` · ${rule.face ?? "—"}/${rule.edge ?? "—"}` : ""})
                    </option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldSideInsertRotation}
                htmlFor="fs-edit-side-insert"
                hint={adminLabels.fairStandItemsFieldSideInsertRotationHint}
              >
                <SuggestTextInput
                  id="fs-edit-side-insert"
                  listId={sideInsertListId}
                  options={fieldOptions.sideInsertRotations}
                  value={form.side_insert_rotation}
                  disabled={saving}
                  onChange={(side_insert_rotation) =>
                    patch("side_insert_rotation", side_insert_rotation)
                  }
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldModelRotationY}
                htmlFor="fs-edit-model-rot"
                hint={adminLabels.fairStandItemsFieldModelRotationYHint}
              >
                <TextInput
                  id="fs-edit-model-rot"
                  type="number"
                  value={form.model_rotation_y_deg}
                  disabled={saving}
                  onChange={(event) => patch("model_rotation_y_deg", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldVisualRotationY}
                htmlFor="fs-edit-visual-rot"
                hint={adminLabels.fairStandItemsFieldVisualRotationYHint}
              >
                <TextInput
                  id="fs-edit-visual-rot"
                  type="number"
                  value={form.visual_rotation_y_deg}
                  disabled={saving}
                  onChange={(event) => patch("visual_rotation_y_deg", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldRotationStep}
                htmlFor="fs-edit-rot-step"
                hint={adminLabels.fairStandItemsFieldRotationStepHint}
              >
                <TextInput
                  id="fs-edit-rot-step"
                  type="number"
                  value={form.rotation_step_deg}
                  disabled={saving}
                  onChange={(event) => patch("rotation_step_deg", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldDefaultRotation}
                htmlFor="fs-edit-default-rot"
                hint={adminLabels.fairStandItemsFieldDefaultRotationHint}
              >
                <TextInput
                  id="fs-edit-default-rot"
                  type="number"
                  value={form.default_rotation_deg}
                  disabled={saving}
                  onChange={(event) => patch("default_rotation_deg", event.target.value)}
                />
              </FormField>
            </FormGrid>
          </Card>
        </TabPanel>

        <TabPanel
          id="panel-edit-dimensions"
          labelledBy="tab-dimensions"
          active={activeTab === "dimensions"}
        >
          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionDimensions}</h3>
            <p className="field-hint">{adminLabels.fairStandItemsDimensionsHint}</p>
            <FormGrid columns={2}>
              {dimensionFields.map(([key, label, hint]) => (
                <FormField key={key} label={label} htmlFor={`fs-edit-${key}`} hint={hint}>
                  <TextInput
                    id={`fs-edit-${key}`}
                    type="number"
                    value={form[key] as string}
                    disabled={saving}
                    onChange={(event) => onChange({ ...form, [key]: event.target.value })}
                  />
                </FormField>
              ))}
            </FormGrid>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionSceneDimensions}</h3>
            <p className="field-hint">{adminLabels.fairStandItemsSceneDimensionsHint}</p>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldWidthCm}
                htmlFor="fs-edit-scene-width"
                hint={adminLabels.fairStandItemsFieldSceneWidthCmHint}
              >
                <TextInput
                  id="fs-edit-scene-width"
                  type="number"
                  value={form.scene_width_cm}
                  disabled={saving}
                  onChange={(event) => patch("scene_width_cm", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldDepthCm}
                htmlFor="fs-edit-scene-depth"
                hint={adminLabels.fairStandItemsFieldSceneDepthCmHint}
              >
                <TextInput
                  id="fs-edit-scene-depth"
                  type="number"
                  value={form.scene_depth_cm}
                  disabled={saving}
                  onChange={(event) => patch("scene_depth_cm", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldHeightCm}
                htmlFor="fs-edit-scene-height"
                hint={adminLabels.fairStandItemsFieldSceneHeightCmHint}
              >
                <TextInput
                  id="fs-edit-scene-height"
                  type="number"
                  value={form.scene_height_cm}
                  disabled={saving}
                  onChange={(event) => patch("scene_height_cm", event.target.value)}
                />
              </FormField>
            </FormGrid>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionStrip}</h3>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldStripAlign}
                htmlFor="fs-edit-strip-align"
                hint={adminLabels.fairStandItemsFieldStripAlignHint}
              >
                <TextInput
                  id="fs-edit-strip-align"
                  value={form.strip_align}
                  disabled={saving}
                  onChange={(event) => patch("strip_align", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldStripCount}
                htmlFor="fs-edit-strip-count"
                hint={adminLabels.fairStandItemsFieldStripCountHint}
              >
                <TextInput
                  id="fs-edit-strip-count"
                  type="number"
                  value={form.strip_count}
                  disabled={saving}
                  onChange={(event) => patch("strip_count", event.target.value)}
                />
              </FormField>
            </FormGrid>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionVideoWall}</h3>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldVideoRows}
                htmlFor="fs-edit-video-rows"
                hint={adminLabels.fairStandItemsFieldVideoRowsHint}
              >
                <TextInput
                  id="fs-edit-video-rows"
                  type="number"
                  value={form.video_rows}
                  disabled={saving}
                  onChange={(event) => patch("video_rows", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldVideoCols}
                htmlFor="fs-edit-video-cols"
                hint={adminLabels.fairStandItemsFieldVideoColsHint}
              >
                <TextInput
                  id="fs-edit-video-cols"
                  type="number"
                  value={form.video_cols}
                  disabled={saving}
                  onChange={(event) => patch("video_cols", event.target.value)}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldPanelItemKey}
                htmlFor="fs-edit-panel-key"
                hint={adminLabels.fairStandItemsFieldPanelItemKeyHint}
              >
                <TextInput
                  id="fs-edit-panel-key"
                  value={form.panel_item_key}
                  disabled={saving}
                  onChange={(event) => patch("panel_item_key", event.target.value)}
                />
              </FormField>
            </FormGrid>
            <Button
              size="sm"
              variant="secondary"
              disabled={saving}
              onClick={() =>
                onChange({ ...form, video_rows: "", video_cols: "", panel_item_key: "" })
              }
            >
              {adminLabels.fairStandItemsClearVideoWall}
            </Button>
          </Card>
        </TabPanel>

        <TabPanel
          id="panel-edit-components"
          labelledBy="tab-components"
          active={activeTab === "components"}
        >
          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionComponents}</h3>
            <p className="field-hint">{adminLabels.fairStandItemsComponentsDescription}</p>
            <UniversalDataTable
              items={form.components.map((row, index) => ({ ...row, index }))}
              columns={editComponentColumns}
              rowKey={(row) => `component-${row.index}`}
              emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyComponents} />}
            />
            <p className="field-hint">{adminLabels.fairStandItemsAddComponentHint}</p>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldChildItemKey}
                htmlFor="fs-add-comp-key"
                hint={adminLabels.fairStandItemsFieldChildItemKeyHint}
              >
                <FairStandItemEntitySelect
                  id="fs-add-comp-key"
                  value={componentDraft.child_item_key}
                  disabled={saving || addingComponent}
                  excludeItemKeys={[
                    itemKey,
                    ...form.components.map((row) => row.child_item_key),
                  ]}
                  onChange={(nextKey) =>
                    setComponentDraft({ ...componentDraft, child_item_key: nextKey })
                  }
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldQuantity}
                htmlFor="fs-add-comp-qty"
                hint={adminLabels.fairStandItemsFieldQuantityHint}
              >
                <TextInput
                  id="fs-add-comp-qty"
                  type="number"
                  value={componentDraft.quantity}
                  disabled={saving || addingComponent}
                  onChange={(event) =>
                    setComponentDraft({ ...componentDraft, quantity: event.target.value })
                  }
                />
              </FormField>
            </FormGrid>
            <Button
              size="sm"
              variant="secondary"
              disabled={saving || addingComponent || !componentDraft.child_item_key.trim()}
              onClick={() => {
                void addComponentFromDraft();
              }}
            >
              {adminLabels.fairStandItemsAddComponent}
            </Button>
          </Card>

          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionBodyParts}</h3>
            <p className="field-hint">{adminLabels.fairStandItemsBodyPartsDescription}</p>
            <UniversalDataTable
              items={form.body_parts.map((row, index) => ({ ...row, index }))}
              columns={editBodyPartColumns}
              rowKey={(row) => `body-${row.index}`}
              emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyBodyParts} />}
            />
            <p className="field-hint">{adminLabels.fairStandItemsAddBodyPartHint}</p>
            <FormGrid columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldChildItemKey}
                htmlFor="fs-add-body-key"
                hint={adminLabels.fairStandItemsFieldChildItemKeyHint}
              >
                <FairStandItemEntitySelect
                  id="fs-add-body-key"
                  value={bodyDraft.child_item_key}
                  disabled={saving || addingBodyPart}
                  excludeItemKeys={[
                    itemKey,
                    ...form.body_parts.map((row) => row.child_item_key),
                  ]}
                  onChange={(nextKey) =>
                    setBodyDraft({ ...bodyDraft, child_item_key: nextKey })
                  }
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldBodyRole}
                htmlFor="fs-add-body-role"
                hint={adminLabels.fairStandItemsFieldBodyRoleHint}
              >
                <TextInput
                  id="fs-add-body-role"
                  value={bodyDraft.body_role}
                  disabled={saving || addingBodyPart}
                  onChange={(event) =>
                    setBodyDraft({ ...bodyDraft, body_role: event.target.value })
                  }
                />
              </FormField>
            </FormGrid>
            <Button
              size="sm"
              variant="secondary"
              disabled={
                saving ||
                addingBodyPart ||
                !bodyDraft.child_item_key.trim() ||
                !bodyDraft.body_role.trim()
              }
              onClick={() => {
                void addBodyPartFromDraft();
              }}
            >
              {adminLabels.fairStandItemsAddBodyPart}
            </Button>
          </Card>
        </TabPanel>

        <TabPanel id="panel-edit-assets" labelledBy="tab-assets" active={activeTab === "assets"}>
          <Card>
            <h3 className="form-section-title">{adminLabels.fairStandItemsSectionAssets}</h3>
            <p className="field-hint">{adminLabels.fairStandItemsAssetsDescription}</p>
            {form.assets.map((asset, index) => (
              <FormGrid key={`asset-${index}`} columns={2}>
                <FormField
                  label={adminLabels.fairStandItemsFieldAssetRole}
                  htmlFor={`fs-asset-role-${index}`}
                  hint={adminLabels.fairStandItemsFieldAssetRoleHint}
                >
                  <TextInput
                    id={`fs-asset-role-${index}`}
                    value={asset.asset_role}
                    disabled={saving}
                    onChange={(event) => {
                      const assets = [...form.assets];
                      assets[index] = { ...asset, asset_role: event.target.value };
                      onChange({ ...form, assets });
                    }}
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandItemsFieldRelativePath}
                  htmlFor={`fs-asset-path-${index}`}
                  hint={adminLabels.fairStandItemsFieldRelativePathHint}
                >
                  <TextInput
                    id={`fs-asset-path-${index}`}
                    value={asset.relative_path}
                    disabled={saving}
                    onChange={(event) => {
                      const assets = [...form.assets];
                      assets[index] = { ...asset, relative_path: event.target.value };
                      onChange({ ...form, assets });
                    }}
                  />
                </FormField>
                <CheckboxField
                  id={`fs-asset-active-${index}`}
                  label={adminLabels.fairStandItemsFieldAssetActive}
                  hint={adminLabels.fairStandItemsFieldAssetActiveHint}
                  checked={asset.is_active}
                  disabled={saving}
                  onChange={(checked) => {
                    const assets = [...form.assets];
                    assets[index] = { ...asset, is_active: checked };
                    onChange({ ...form, assets });
                  }}
                />
                <div>
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={saving}
                    onClick={() =>
                      onChange({
                        ...form,
                        assets: form.assets.filter((_, assetIndex) => assetIndex !== index),
                      })
                    }
                  >
                    {adminLabels.fairStandItemsRemoveAsset}
                  </Button>
                </div>
              </FormGrid>
            ))}
            <Button
              size="sm"
              variant="secondary"
              disabled={saving}
              onClick={() =>
                onChange({
                  ...form,
                  assets: [...form.assets, { asset_role: "", relative_path: "", is_active: true }],
                })
              }
            >
              {adminLabels.fairStandItemsAddAsset}
            </Button>
          </Card>
        </TabPanel>

        <FormActions
          onCancel={requestBack}
          cancelLabel={adminLabels.fairStandItemsBack}
          submitLabel={adminLabels.fairStandItemsSave}
          saving={saving}
        />
      </form>
      {removeTarget ? (
        <ConfirmDialog
          title={
            removeTarget.kind === "component"
              ? adminLabels.fairStandItemsRemoveComponentConfirmTitle
              : adminLabels.fairStandItemsRemoveBodyPartConfirmTitle
          }
          message={
            removeTarget.kind === "component"
              ? adminLabels.fairStandItemsRemoveComponentConfirmMessage
              : adminLabels.fairStandItemsRemoveBodyPartConfirmMessage
          }
          confirmLabel={adminLabels.fairStandItemsRemoveConfirm}
          cancelLabel={adminLabels.fairStandItemsCancel}
          variant="danger"
          onCancel={() => setRemoveTarget(null)}
          onConfirm={() => {
            if (removeTarget.kind === "component") {
              onChange({
                ...formRef.current,
                components: formRef.current.components.filter(
                  (_, index) => index !== removeTarget.index,
                ),
              });
            } else {
              onChange({
                ...formRef.current,
                body_parts: formRef.current.body_parts.filter(
                  (_, index) => index !== removeTarget.index,
                ),
              });
            }
            setRemoveTarget(null);
          }}
        />
      ) : null}
    </>
  );
}
