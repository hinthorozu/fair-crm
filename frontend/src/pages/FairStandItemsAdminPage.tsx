import React from "react";
import {
  archiveFairStandAdminItemRecord,
  createFairStandAdminItemRecord,
  getFairStandAdminItemRecord,
  listFairStandAdminItemRecords,
  restoreFairStandAdminItemRecord,
  updateFairStandAdminItemRecord,
  type FairStandAdminItemRecord,
  type FairStandAdminItemAsset,
  type FairStandAdminItemBodyPart,
  type FairStandAdminItemComponent,
  type FairStandAdminItemRecordSummary,
} from "../api/fairStandAdmin";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  CheckboxField,
  FormActions,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormSection,
  TextInput,
  useFormDirtyCancel,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  FAIR_STAND_ITEMS_ARCHIVE,
  FAIR_STAND_ITEMS_CREATE,
  FAIR_STAND_ITEMS_READ,
  FAIR_STAND_ITEMS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type View = "list" | "detail" | "create" | "edit";

type CreateForm = {
  item_key: string;
  name: string;
  item_type: string;
};

type AssetFormRow = { asset_role: string; relative_path: string; is_active: boolean };
type ComponentFormRow = { child_item_key: string; quantity: string; sort_order: string };
type BodyPartFormRow = { body_role: string; child_item_key: string };

type EditForm = {
  name: string;
  item_type: string;
  unit: string;
  material: string;
  panel_role: string;
  connector_type: string;
  shape: string;
  variant: string;
  composition_mode: string;
  composition_module_type: string;
  side_insert_rotation: string;
  snap_target_item_type: string;
  snap_anchor: string;
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
  length_cm: string;
  thickness_cm: string;
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

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function str(value: string | number | null | undefined): string {
  return value == null ? "" : String(value);
}

function yesNo(value: boolean | null | undefined): string {
  return value ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo;
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
    panel_role: str(detail.panelRole),
    connector_type: str(detail.connectorType),
    shape: str(detail.shape),
    variant: str(detail.variant),
    composition_mode: str(detail.compositionMode),
    composition_module_type: str(detail.compositionModuleType),
    side_insert_rotation: str(detail.sideInsertRotation),
    snap_target_item_type: str(detail.snapTargetItemType),
    snap_anchor: str(detail.snapAnchor),
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
    length_cm: str(dims?.lengthCm),
    thickness_cm: str(dims?.thicknessCm),
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
      quantity: str(component.quantity),
      sort_order: str(component.sortOrder),
    })),
    body_parts: detail.bodyParts.map((part) => ({
      body_role: part.bodyRole,
      child_item_key: part.childItemKey,
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
    form.length_cm,
    form.thickness_cm,
    form.mount_height_cm,
    form.wall_gap_cm,
  )
    ? {
        width_cm: optionalNumber(form.width_cm),
        depth_cm: optionalNumber(form.depth_cm),
        height_cm: optionalNumber(form.height_cm),
        length_cm: optionalNumber(form.length_cm),
        thickness_cm: optionalNumber(form.thickness_cm),
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
    panel_role: form.panel_role.trim() || null,
    connector_type: form.connector_type.trim() || null,
    shape: form.shape.trim() || null,
    variant: form.variant.trim() || null,
    composition_mode: form.composition_mode.trim() || null,
    composition_module_type: form.composition_module_type.trim() || null,
    side_insert_rotation: form.side_insert_rotation.trim() || null,
    snap_target_item_type: form.snap_target_item_type.trim() || null,
    snap_anchor: form.snap_anchor.trim() || null,
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
    components: form.components.map((component, index) => ({
      child_item_key: requireText(component.child_item_key, adminLabels.fairStandItemsFieldChildItemKey),
      quantity: optionalNumber(component.quantity) ?? 0,
      sort_order: optionalInt(component.sort_order) ?? index,
    })),
    body_parts: form.body_parts.map((part) => ({
      body_role: requireText(part.body_role, adminLabels.fairStandItemsFieldBodyRole),
      child_item_key: requireText(part.child_item_key, adminLabels.fairStandItemsFieldChildItemKey),
    })),
    video_wall,
  };
}

/** Read-only preview field: label, value (— when empty) and the shared FormField hint. */
function DetailField({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  const isEmpty = value == null || value === "";
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="field-value">{isEmpty ? "—" : value}</div>
      {hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  );
}

export function FairStandItemsAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_ITEMS_READ);
  const canCreate = granted.has(FAIR_STAND_ITEMS_CREATE);
  const canUpdate = granted.has(FAIR_STAND_ITEMS_UPDATE);
  const canArchive = granted.has(FAIR_STAND_ITEMS_ARCHIVE);

  const [view, setView] = React.useState<View>("list");
  const [items, setItems] = React.useState<FairStandAdminItemRecordSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<FairStandAdminItemRecord | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [createForm, setCreateForm] = React.useState<CreateForm | null>(null);
  const [editKey, setEditKey] = React.useState<string | null>(null);
  const [editForm, setEditForm] = React.useState<EditForm | null>(null);
  const [editBaseline, setEditBaseline] = React.useState<EditForm | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [archiveTargetKey, setArchiveTargetKey] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listFairStandAdminItemRecords());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandItemsLoadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const reloadDetail = React.useCallback(async (itemKey: string) => {
    try {
      setDetail(await getFairStandAdminItemRecord(itemKey));
    } catch (detailError) {
      setError(
        detailError instanceof Error ? detailError.message : adminLabels.fairStandItemsDetailLoadError,
      );
    }
  }, []);

  const openDetail = async (itemKey: string) => {
    setSuccess(null);
    setError(null);
    setDetailLoading(true);
    try {
      const record = await getFairStandAdminItemRecord(itemKey);
      setDetail(record);
      setView("detail");
    } catch (detailError) {
      setError(
        detailError instanceof Error ? detailError.message : adminLabels.fairStandItemsDetailLoadError,
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const backToList = () => {
    setView("list");
    setDetail(null);
  };

  const openCreate = () => {
    setSuccess(null);
    setError(null);
    setCreateForm({ ...emptyCreate });
    setView("create");
  };

  const cancelCreate = () => {
    setCreateForm(null);
    setView("list");
  };

  const openEditFromDetail = () => {
    if (!canUpdate || !detail) return;
    setSuccess(null);
    setError(null);
    const form = detailToForm(detail);
    setEditKey(detail.itemKey);
    setEditForm(form);
    setEditBaseline(form);
    setView("edit");
  };

  const backToDetail = () => {
    setEditForm(null);
    setEditBaseline(null);
    setView("detail");
    if (editKey) void reloadDetail(editKey);
  };

  const saveCreate = async () => {
    if (!canCreate || !createForm) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const record = await createFairStandAdminItemRecord({
        item_key: requireText(createForm.item_key, adminLabels.fairStandItemsFieldItemKey),
        name: requireText(createForm.name, adminLabels.fairStandItemsFieldName),
        item_type: requireText(createForm.item_type, adminLabels.fairStandItemsFieldItemType),
      });
      setCreateForm(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      setDetail(record);
      setView("detail");
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandItemsSaveError);
    } finally {
      setSaving(false);
    }
  };

  const saveEdit = async () => {
    if (!canUpdate || !editKey || !editForm) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const record = await updateFairStandAdminItemRecord(editKey, buildUpdatePayload(editForm));
      setEditForm(null);
      setEditBaseline(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      setDetail(record);
      setView("detail");
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandItemsSaveError);
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async (itemKey: string) => {
    try {
      await archiveFairStandAdminItemRecord(itemKey);
      setArchiveTargetKey(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      await load();
      if (detail && detail.itemKey === itemKey) await reloadDetail(itemKey);
    } catch (archiveError) {
      setArchiveTargetKey(null);
      setError(
        archiveError instanceof Error ? archiveError.message : adminLabels.fairStandItemsArchiveError,
      );
    }
  };

  const handleRestore = async (itemKey: string) => {
    try {
      await restoreFairStandAdminItemRecord(itemKey);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      await load();
      if (detail && detail.itemKey === itemKey) await reloadDetail(itemKey);
    } catch (restoreError) {
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
      render: (row) => (row.catalogVisible ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo),
    },
    {
      key: "isRender",
      title: adminLabels.fairStandItemsColIsRender,
      sortable: true,
      render: (row) => (row.isRender ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo),
    },
    {
      key: "componentCount",
      title: adminLabels.fairStandItemsColComponentCount,
      sortable: true,
      render: (row) => String(row.componentCount),
    },
    {
      key: "assetCount",
      title: adminLabels.fairStandItemsColAssetCount,
      sortable: true,
      render: (row) => String(row.assetCount),
    },
    {
      key: "status",
      title: adminLabels.fairStandItemsColStatus,
      sortable: true,
      render: (row) =>
        row.isActive ? adminLabels.fairStandItemsStatusActive : adminLabels.fairStandItemsStatusInactive,
    },
    {
      key: "actions",
      title: adminLabels.fairStandItemsColActions,
      sortable: false,
      render: (row) => (
        <TableRowActions>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              void openDetail(row.itemKey);
            }}
          >
            {adminLabels.fairStandItemsActionView}
          </Button>
          {canArchive && row.isActive ? (
            <Button size="sm" variant="danger" onClick={() => setArchiveTargetKey(row.itemKey)}>
              {adminLabels.fairStandItemsActionArchive}
            </Button>
          ) : null}
          {canArchive && !row.isActive ? (
            <Button
              size="sm"
              onClick={() => {
                void handleRestore(row.itemKey);
              }}
            >
              {adminLabels.fairStandItemsActionRestore}
            </Button>
          ) : null}
        </TableRowActions>
      ),
    },
  ];

  const banners = (
    <>
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
    </>
  );

  return (
    <PageShell>
      {view === "list" ? (
        <>
          <PageHeader
            title={adminLabels.fairStandItemsTitle}
            subtitle={adminLabels.fairStandItemsSubtitle}
            actions={
              canCreate ? (
                <Button variant="primary" onClick={openCreate}>
                  {adminLabels.fairStandItemsCreate}
                </Button>
              ) : null
            }
          />
          {banners}
          {!canRead ? <Banner variant="info">{adminLabels.fairStandItemsPermissionDenied}</Banner> : null}
          {loading || detailLoading ? <LoadingState /> : null}
          {canRead && !loading ? (
            <UniversalDataTable
              items={items}
              columns={columns}
              rowKey={(row) => row.itemKey}
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandItemsEmptyTitle}
                  description={adminLabels.fairStandItemsEmptyDescription}
                />
              }
            />
          ) : null}
        </>
      ) : null}

      {view === "detail" && detail ? (
        <ItemDetailView
          detail={detail}
          banners={banners}
          canUpdate={canUpdate}
          canArchive={canArchive}
          onBack={backToList}
          onEdit={openEditFromDetail}
          onArchive={() => setArchiveTargetKey(detail.itemKey)}
          onRestore={() => {
            void handleRestore(detail.itemKey);
          }}
        />
      ) : null}

      {view === "create" && createForm ? (
        <FormDirtyHost onClose={cancelCreate}>
          <ItemCreateView
            form={createForm}
            saving={saving}
            banners={banners}
            onChange={setCreateForm}
            onSubmit={saveCreate}
          />
        </FormDirtyHost>
      ) : null}

      {view === "edit" && editForm && editBaseline && editKey ? (
        <FormDirtyHost onClose={backToDetail}>
          <ItemEditView
            itemKey={editKey}
            title={detail ? detail.name : editKey}
            form={editForm}
            baseline={editBaseline}
            saving={saving}
            banners={banners}
            onChange={setEditForm}
            onSubmit={saveEdit}
          />
        </FormDirtyHost>
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

const componentColumns: UniversalDataTableColumn<FairStandAdminItemComponent>[] = [
  {
    key: "childItemKey",
    title: adminLabels.fairStandItemsFieldChildItemKey,
    sortable: false,
    render: (row) => row.childItemKey,
  },
  {
    key: "quantity",
    title: adminLabels.fairStandItemsFieldQuantity,
    sortable: false,
    render: (row) => String(row.quantity),
  },
  {
    key: "sortOrder",
    title: adminLabels.fairStandItemsFieldSortOrder,
    sortable: false,
    render: (row) => String(row.sortOrder),
  },
];

const bodyPartColumns: UniversalDataTableColumn<FairStandAdminItemBodyPart>[] = [
  {
    key: "bodyRole",
    title: adminLabels.fairStandItemsFieldBodyRole,
    sortable: false,
    render: (row) => row.bodyRole,
  },
  {
    key: "childItemKey",
    title: adminLabels.fairStandItemsFieldChildItemKey,
    sortable: false,
    render: (row) => row.childItemKey,
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
    render: (row) => (row.isActive ? adminLabels.fairStandItemsYes : adminLabels.fairStandItemsNo),
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
  const actions: PageHeaderAction[] = [];
  if (canUpdate) {
    actions.push({
      id: "edit",
      label: adminLabels.fairStandItemsActionEdit,
      onClick: onEdit,
      variant: "secondary",
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

  const dims = detail.dimensions;
  const scene = detail.sceneDimensions;
  const strip = detail.stripOccupancy;
  const video = detail.videoWall;

  return (
    <>
      <PageHeader
        title={`${detail.name} · ${detail.itemKey}`}
        subtitle={adminLabels.fairStandItemsDetailSubtitle}
        breadcrumbs={[
          { label: adminLabels.fairStandItemsBackToList, onClick: onBack },
          { label: detail.name, current: true },
        ]}
        actions={actions}
      />
      {banners}

      <FormSection title={adminLabels.fairStandItemsSectionIdentity}>
        <FormGrid columns={2}>
          <DetailField
            label={adminLabels.fairStandItemsFieldItemKey}
            value={detail.itemKey}
            hint={adminLabels.fairStandItemsFieldItemKeyHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldName}
            value={detail.name}
            hint={adminLabels.fairStandItemsFieldNameHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldItemType}
            value={detail.type}
            hint={adminLabels.fairStandItemsFieldItemTypeHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldUnit}
            value={detail.unit}
            hint={adminLabels.fairStandItemsFieldUnitHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldMaterial}
            value={detail.material}
            hint={adminLabels.fairStandItemsFieldMaterialHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldPanelRole}
            value={detail.panelRole}
            hint={adminLabels.fairStandItemsFieldPanelRoleHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldConnectorType}
            value={detail.connectorType}
            hint={adminLabels.fairStandItemsFieldConnectorTypeHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldShape}
            value={detail.shape}
            hint={adminLabels.fairStandItemsFieldShapeHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldVariant}
            value={detail.variant}
            hint={adminLabels.fairStandItemsFieldVariantHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldCompositionMode}
            value={detail.compositionMode}
            hint={adminLabels.fairStandItemsFieldCompositionModeHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldCompositionModuleType}
            value={detail.compositionModuleType}
            hint={adminLabels.fairStandItemsFieldCompositionModuleTypeHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldSideInsertRotation}
            value={detail.sideInsertRotation}
            hint={adminLabels.fairStandItemsFieldSideInsertRotationHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldSnapTarget}
            value={detail.snapTargetItemType}
            hint={adminLabels.fairStandItemsFieldSnapTargetHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldSnapAnchor}
            value={detail.snapAnchor}
            hint={adminLabels.fairStandItemsFieldSnapAnchorHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldDefaultZ}
            value={str(detail.defaultZCm)}
            hint={adminLabels.fairStandItemsFieldDefaultZHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldDefaultColor}
            value={str(detail.defaultColor)}
            hint={adminLabels.fairStandItemsFieldDefaultColorHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldEyeCount}
            value={str(detail.eyeCount)}
            hint={adminLabels.fairStandItemsFieldEyeCountHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldModelRotationY}
            value={str(detail.modelRotationYDeg)}
            hint={adminLabels.fairStandItemsFieldModelRotationYHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldVisualRotationY}
            value={str(detail.visualRotationYDeg)}
            hint={adminLabels.fairStandItemsFieldVisualRotationYHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldRotationStep}
            value={str(detail.rotationStepDeg)}
            hint={adminLabels.fairStandItemsFieldRotationStepHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldDefaultRotation}
            value={str(detail.defaultRotationDeg)}
            hint={adminLabels.fairStandItemsFieldDefaultRotationHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldIsActive}
            value={yesNo(detail.isActive)}
            hint={adminLabels.fairStandItemsFieldIsActiveHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldIsRender}
            value={yesNo(detail.isRender)}
            hint={adminLabels.fairStandItemsFieldIsRenderHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldPreserveModelScale}
            value={yesNo(detail.preserveModelScale)}
            hint={adminLabels.fairStandItemsFieldPreserveModelScaleHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldPaintable}
            value={yesNo(detail.paintable)}
            hint={adminLabels.fairStandItemsFieldPaintableHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldAcceptsColor}
            value={yesNo(detail.acceptsColor)}
            hint={adminLabels.fairStandItemsFieldAcceptsColorHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldAcceptsImage}
            value={yesNo(detail.acceptsImage)}
            hint={adminLabels.fairStandItemsFieldAcceptsImageHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldAcceptsLightbox}
            value={yesNo(detail.acceptsLightbox)}
            hint={adminLabels.fairStandItemsFieldAcceptsLightboxHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldAcceptsGlass}
            value={yesNo(detail.acceptsGlass)}
            hint={adminLabels.fairStandItemsFieldAcceptsGlassHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldAcceptsMesh}
            value={yesNo(detail.acceptsMesh)}
            hint={adminLabels.fairStandItemsFieldAcceptsMeshHint}
          />
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionCatalog}>
        <FormGrid columns={2}>
          <DetailField
            label={adminLabels.fairStandItemsFieldCatalogVisible}
            value={yesNo(detail.catalogVisible)}
            hint={adminLabels.fairStandItemsFieldCatalogVisibleHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldCategoryId}
            value={str(detail.categoryId)}
            hint={adminLabels.fairStandItemsFieldCategoryIdHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldCatalogItemIndex}
            value={str(detail.catalogItemIndex)}
            hint={adminLabels.fairStandItemsFieldCatalogItemIndexHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldPreviewId}
            value={str(detail.previewId)}
            hint={adminLabels.fairStandItemsFieldPreviewIdHint}
          />
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionDimensions}>
        <FormGrid columns={2}>
          <DetailField
            label={adminLabels.fairStandItemsFieldWidthCm}
            value={str(dims?.widthCm)}
            hint={adminLabels.fairStandItemsFieldWidthCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldDepthCm}
            value={str(dims?.depthCm)}
            hint={adminLabels.fairStandItemsFieldDepthCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldHeightCm}
            value={str(dims?.heightCm)}
            hint={adminLabels.fairStandItemsFieldHeightCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldLengthCm}
            value={str(dims?.lengthCm)}
            hint={adminLabels.fairStandItemsFieldLengthCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldThicknessCm}
            value={str(dims?.thicknessCm)}
            hint={adminLabels.fairStandItemsFieldThicknessCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldMountHeightCm}
            value={str(dims?.mountHeightCm)}
            hint={adminLabels.fairStandItemsFieldMountHeightCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldWallGapCm}
            value={str(dims?.wallGapCm)}
            hint={adminLabels.fairStandItemsFieldWallGapCmHint}
          />
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionSceneDimensions}>
        <FormGrid columns={2}>
          <DetailField
            label={adminLabels.fairStandItemsFieldWidthCm}
            value={str(scene?.widthCm)}
            hint={adminLabels.fairStandItemsFieldSceneWidthCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldDepthCm}
            value={str(scene?.depthCm)}
            hint={adminLabels.fairStandItemsFieldSceneDepthCmHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldHeightCm}
            value={str(scene?.heightCm)}
            hint={adminLabels.fairStandItemsFieldSceneHeightCmHint}
          />
        </FormGrid>
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionStrip}>
        <FormGrid columns={2}>
          <DetailField
            label={adminLabels.fairStandItemsFieldStripAlign}
            value={strip?.align}
            hint={adminLabels.fairStandItemsFieldStripAlignHint}
          />
          <DetailField
            label={adminLabels.fairStandItemsFieldStripCount}
            value={str(strip?.stripCount)}
            hint={adminLabels.fairStandItemsFieldStripCountHint}
          />
        </FormGrid>
      </FormSection>

      {video ? (
        <FormSection title={adminLabels.fairStandItemsSectionVideoWall}>
          <FormGrid columns={2}>
            <DetailField
              label={adminLabels.fairStandItemsFieldVideoRows}
              value={str(video.rows)}
              hint={adminLabels.fairStandItemsFieldVideoRowsHint}
            />
            <DetailField
              label={adminLabels.fairStandItemsFieldVideoCols}
              value={str(video.cols)}
              hint={adminLabels.fairStandItemsFieldVideoColsHint}
            />
            <DetailField
              label={adminLabels.fairStandItemsFieldPanelItemKey}
              value={video.panelItemKey}
              hint={adminLabels.fairStandItemsFieldPanelItemKeyHint}
            />
          </FormGrid>
        </FormSection>
      ) : null}

      <FormSection title={adminLabels.fairStandItemsSectionComponents}>
        <p className="field-hint">{adminLabels.fairStandItemsComponentsDescription}</p>
        <UniversalDataTable
          items={detail.components}
          columns={componentColumns}
          rowKey={(row) => row.id}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyComponents} />}
        />
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionBodyParts}>
        <p className="field-hint">{adminLabels.fairStandItemsBodyPartsDescription}</p>
        <UniversalDataTable
          items={detail.bodyParts}
          columns={bodyPartColumns}
          rowKey={(row) => `${row.bodyRole}-${row.childItemKey}`}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyBodyParts} />}
        />
      </FormSection>

      <FormSection title={adminLabels.fairStandItemsSectionAssets}>
        <p className="field-hint">{adminLabels.fairStandItemsAssetsDescription}</p>
        <UniversalDataTable
          items={detail.assets}
          columns={assetColumns}
          rowKey={(row) => row.id}
          emptyState={<EmptyState title={adminLabels.fairStandItemsEmptyAssets} />}
        />
      </FormSection>
    </>
  );
}

function ItemCreateView({
  form,
  saving,
  banners,
  onChange,
  onSubmit,
}: {
  form: CreateForm;
  saving: boolean;
  banners: React.ReactNode;
  onChange: (form: CreateForm) => void;
  onSubmit: () => void;
}) {
  const requestBack = useFormDirtyCancel(() => undefined);

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
                onChange={(event) => onChange({ ...form, item_key: event.target.value })}
                required
              />
            </FormField>
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
                onChange={(event) => onChange({ ...form, name: event.target.value })}
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
              <TextInput
                id="fs-item-type"
                value={form.item_type}
                disabled={saving}
                onChange={(event) => onChange({ ...form, item_type: event.target.value })}
                required
              />
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
  saving,
  banners,
  onChange,
  onSubmit,
}: {
  itemKey: string;
  title: string;
  form: EditForm;
  baseline: EditForm;
  saving: boolean;
  banners: React.ReactNode;
  onChange: (form: EditForm) => void;
  onSubmit: () => void;
}) {
  const requestBack = useFormDirtyCancel(() => undefined);

  const dimensionFields: [keyof EditForm, string, string][] = [
    ["width_cm", adminLabels.fairStandItemsFieldWidthCm, adminLabels.fairStandItemsFieldWidthCmHint],
    ["depth_cm", adminLabels.fairStandItemsFieldDepthCm, adminLabels.fairStandItemsFieldDepthCmHint],
    ["height_cm", adminLabels.fairStandItemsFieldHeightCm, adminLabels.fairStandItemsFieldHeightCmHint],
    ["length_cm", adminLabels.fairStandItemsFieldLengthCm, adminLabels.fairStandItemsFieldLengthCmHint],
    [
      "thickness_cm",
      adminLabels.fairStandItemsFieldThicknessCm,
      adminLabels.fairStandItemsFieldThicknessCmHint,
    ],
    [
      "mount_height_cm",
      adminLabels.fairStandItemsFieldMountHeightCm,
      adminLabels.fairStandItemsFieldMountHeightCmHint,
    ],
    ["wall_gap_cm", adminLabels.fairStandItemsFieldWallGapCm, adminLabels.fairStandItemsFieldWallGapCmHint],
  ];

  return (
    <>
      <FormDirtyReporter values={form} baseline={baseline} />
      <PageHeader
        title={`${title} · ${itemKey}`}
        subtitle={adminLabels.fairStandItemsEditTitle}
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
        <FormSection title={adminLabels.fairStandItemsSectionIdentity}>
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
                onChange={(event) => onChange({ ...form, name: event.target.value })}
                required
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldItemType}
              htmlFor="fs-edit-type"
              hint={adminLabels.fairStandItemsFieldItemTypeHint}
              required
            >
              <TextInput
                id="fs-edit-type"
                value={form.item_type}
                disabled={saving}
                onChange={(event) => onChange({ ...form, item_type: event.target.value })}
                required
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldUnit}
              htmlFor="fs-edit-unit"
              hint={adminLabels.fairStandItemsFieldUnitHint}
            >
              <TextInput
                id="fs-edit-unit"
                value={form.unit}
                disabled={saving}
                onChange={(event) => onChange({ ...form, unit: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldMaterial}
              htmlFor="fs-edit-material"
              hint={adminLabels.fairStandItemsFieldMaterialHint}
            >
              <TextInput
                id="fs-edit-material"
                value={form.material}
                disabled={saving}
                onChange={(event) => onChange({ ...form, material: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldPanelRole}
              htmlFor="fs-edit-panel-role"
              hint={adminLabels.fairStandItemsFieldPanelRoleHint}
            >
              <TextInput
                id="fs-edit-panel-role"
                value={form.panel_role}
                disabled={saving}
                onChange={(event) => onChange({ ...form, panel_role: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldConnectorType}
              htmlFor="fs-edit-connector"
              hint={adminLabels.fairStandItemsFieldConnectorTypeHint}
            >
              <TextInput
                id="fs-edit-connector"
                value={form.connector_type}
                disabled={saving}
                onChange={(event) => onChange({ ...form, connector_type: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldShape}
              htmlFor="fs-edit-shape"
              hint={adminLabels.fairStandItemsFieldShapeHint}
            >
              <TextInput
                id="fs-edit-shape"
                value={form.shape}
                disabled={saving}
                onChange={(event) => onChange({ ...form, shape: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldVariant}
              htmlFor="fs-edit-variant"
              hint={adminLabels.fairStandItemsFieldVariantHint}
            >
              <TextInput
                id="fs-edit-variant"
                value={form.variant}
                disabled={saving}
                onChange={(event) => onChange({ ...form, variant: event.target.value })}
              />
            </FormField>
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
                onChange={(event) => onChange({ ...form, default_z_cm: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldSnapTarget}
              htmlFor="fs-edit-snap-target"
              hint={adminLabels.fairStandItemsFieldSnapTargetHint}
            >
              <TextInput
                id="fs-edit-snap-target"
                value={form.snap_target_item_type}
                disabled={saving}
                onChange={(event) => onChange({ ...form, snap_target_item_type: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldSnapAnchor}
              htmlFor="fs-edit-snap-anchor"
              hint={adminLabels.fairStandItemsFieldSnapAnchorHint}
            >
              <TextInput
                id="fs-edit-snap-anchor"
                value={form.snap_anchor}
                disabled={saving}
                onChange={(event) => onChange({ ...form, snap_anchor: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldCompositionMode}
              htmlFor="fs-edit-comp-mode"
              hint={adminLabels.fairStandItemsFieldCompositionModeHint}
            >
              <TextInput
                id="fs-edit-comp-mode"
                value={form.composition_mode}
                disabled={saving}
                onChange={(event) => onChange({ ...form, composition_mode: event.target.value })}
              />
            </FormField>
          </FormGrid>
          <CheckboxField
            id="fs-edit-is-active"
            label={adminLabels.fairStandItemsFieldIsActive}
            hint={adminLabels.fairStandItemsFieldIsActiveHint}
            checked={form.is_active}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, is_active: checked })}
          />
          <CheckboxField
            id="fs-edit-is-render"
            label={adminLabels.fairStandItemsFieldIsRender}
            hint={adminLabels.fairStandItemsFieldIsRenderHint}
            checked={form.is_render}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, is_render: checked })}
          />
          <CheckboxField
            id="fs-edit-preserve-scale"
            label={adminLabels.fairStandItemsFieldPreserveModelScale}
            hint={adminLabels.fairStandItemsFieldPreserveModelScaleHint}
            checked={form.preserve_model_scale}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, preserve_model_scale: checked })}
          />
          <CheckboxField
            id="fs-edit-paintable"
            label={adminLabels.fairStandItemsFieldPaintable}
            hint={adminLabels.fairStandItemsFieldPaintableHint}
            checked={form.paintable}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, paintable: checked })}
          />
          <CheckboxField
            id="fs-edit-accepts-color"
            label={adminLabels.fairStandItemsFieldAcceptsColor}
            hint={adminLabels.fairStandItemsFieldAcceptsColorHint}
            checked={form.accepts_color}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, accepts_color: checked })}
          />
          <CheckboxField
            id="fs-edit-accepts-image"
            label={adminLabels.fairStandItemsFieldAcceptsImage}
            hint={adminLabels.fairStandItemsFieldAcceptsImageHint}
            checked={form.accepts_image}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, accepts_image: checked })}
          />
          <CheckboxField
            id="fs-edit-accepts-lightbox"
            label={adminLabels.fairStandItemsFieldAcceptsLightbox}
            hint={adminLabels.fairStandItemsFieldAcceptsLightboxHint}
            checked={form.accepts_lightbox}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, accepts_lightbox: checked })}
          />
          <CheckboxField
            id="fs-edit-accepts-glass"
            label={adminLabels.fairStandItemsFieldAcceptsGlass}
            hint={adminLabels.fairStandItemsFieldAcceptsGlassHint}
            checked={form.accepts_glass}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, accepts_glass: checked })}
          />
          <CheckboxField
            id="fs-edit-accepts-mesh"
            label={adminLabels.fairStandItemsFieldAcceptsMesh}
            hint={adminLabels.fairStandItemsFieldAcceptsMeshHint}
            checked={form.accepts_mesh}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, accepts_mesh: checked })}
          />
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionCatalog}>
          <FormGrid columns={2}>
            <FormField
              label={adminLabels.fairStandItemsFieldCategoryId}
              htmlFor="fs-edit-category"
              hint={adminLabels.fairStandItemsFieldCategoryIdHint}
            >
              <TextInput
                id="fs-edit-category"
                type="number"
                value={form.category_id}
                disabled={saving}
                onChange={(event) => onChange({ ...form, category_id: event.target.value })}
              />
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
                onChange={(event) => onChange({ ...form, catalog_item_index: event.target.value })}
              />
            </FormField>
            <FormField
              label={adminLabels.fairStandItemsFieldPreviewId}
              htmlFor="fs-edit-preview"
              hint={adminLabels.fairStandItemsFieldPreviewIdHint}
            >
              <TextInput
                id="fs-edit-preview"
                type="number"
                value={form.preview_id}
                disabled={saving}
                onChange={(event) => onChange({ ...form, preview_id: event.target.value })}
              />
            </FormField>
          </FormGrid>
          <CheckboxField
            id="fs-edit-catalog-visible"
            label={adminLabels.fairStandItemsFieldCatalogVisible}
            hint={adminLabels.fairStandItemsFieldCatalogVisibleHint}
            checked={form.catalog_visible}
            disabled={saving}
            onChange={(checked) => onChange({ ...form, catalog_visible: checked })}
          />
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionDimensions}>
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
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionSceneDimensions}>
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
                onChange={(event) => onChange({ ...form, scene_width_cm: event.target.value })}
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
                onChange={(event) => onChange({ ...form, scene_depth_cm: event.target.value })}
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
                onChange={(event) => onChange({ ...form, scene_height_cm: event.target.value })}
              />
            </FormField>
          </FormGrid>
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionStrip}>
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
                onChange={(event) => onChange({ ...form, strip_align: event.target.value })}
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
                onChange={(event) => onChange({ ...form, strip_count: event.target.value })}
              />
            </FormField>
          </FormGrid>
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionAssets}>
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
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionComponents}>
          <p className="field-hint">{adminLabels.fairStandItemsComponentsDescription}</p>
          {form.components.map((component, index) => (
            <FormGrid key={`component-${index}`} columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldChildItemKey}
                htmlFor={`fs-comp-child-${index}`}
                hint={adminLabels.fairStandItemsFieldChildItemKeyHint}
              >
                <TextInput
                  id={`fs-comp-child-${index}`}
                  value={component.child_item_key}
                  disabled={saving}
                  onChange={(event) => {
                    const components = [...form.components];
                    components[index] = { ...component, child_item_key: event.target.value };
                    onChange({ ...form, components });
                  }}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldQuantity}
                htmlFor={`fs-comp-qty-${index}`}
                hint={adminLabels.fairStandItemsFieldQuantityHint}
              >
                <TextInput
                  id={`fs-comp-qty-${index}`}
                  type="number"
                  value={component.quantity}
                  disabled={saving}
                  onChange={(event) => {
                    const components = [...form.components];
                    components[index] = { ...component, quantity: event.target.value };
                    onChange({ ...form, components });
                  }}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldSortOrder}
                htmlFor={`fs-comp-sort-${index}`}
                hint={adminLabels.fairStandItemsFieldSortOrderHint}
              >
                <TextInput
                  id={`fs-comp-sort-${index}`}
                  type="number"
                  value={component.sort_order}
                  disabled={saving}
                  onChange={(event) => {
                    const components = [...form.components];
                    components[index] = { ...component, sort_order: event.target.value };
                    onChange({ ...form, components });
                  }}
                />
              </FormField>
              <div>
                <Button
                  size="sm"
                  variant="danger"
                  disabled={saving}
                  onClick={() =>
                    onChange({
                      ...form,
                      components: form.components.filter(
                        (_, componentIndex) => componentIndex !== index,
                      ),
                    })
                  }
                >
                  {adminLabels.fairStandItemsRemoveComponent}
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
                components: [
                  ...form.components,
                  {
                    child_item_key: "",
                    quantity: "1",
                    sort_order: String(form.components.length),
                  },
                ],
              })
            }
          >
            {adminLabels.fairStandItemsAddComponent}
          </Button>
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionBodyParts}>
          {form.body_parts.map((part, index) => (
            <FormGrid key={`body-${index}`} columns={2}>
              <FormField
                label={adminLabels.fairStandItemsFieldBodyRole}
                htmlFor={`fs-body-role-${index}`}
                hint={adminLabels.fairStandItemsFieldBodyRoleHint}
              >
                <TextInput
                  id={`fs-body-role-${index}`}
                  value={part.body_role}
                  disabled={saving}
                  onChange={(event) => {
                    const body_parts = [...form.body_parts];
                    body_parts[index] = { ...part, body_role: event.target.value };
                    onChange({ ...form, body_parts });
                  }}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldChildItemKey}
                htmlFor={`fs-body-child-${index}`}
                hint={adminLabels.fairStandItemsFieldChildItemKeyHint}
              >
                <TextInput
                  id={`fs-body-child-${index}`}
                  value={part.child_item_key}
                  disabled={saving}
                  onChange={(event) => {
                    const body_parts = [...form.body_parts];
                    body_parts[index] = { ...part, child_item_key: event.target.value };
                    onChange({ ...form, body_parts });
                  }}
                />
              </FormField>
              <div>
                <Button
                  size="sm"
                  variant="danger"
                  disabled={saving}
                  onClick={() =>
                    onChange({
                      ...form,
                      body_parts: form.body_parts.filter((_, partIndex) => partIndex !== index),
                    })
                  }
                >
                  {adminLabels.fairStandItemsRemoveBodyPart}
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
                body_parts: [...form.body_parts, { body_role: "", child_item_key: "" }],
              })
            }
          >
            {adminLabels.fairStandItemsAddBodyPart}
          </Button>
        </FormSection>

        <FormSection title={adminLabels.fairStandItemsSectionVideoWall}>
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
                onChange={(event) => onChange({ ...form, video_rows: event.target.value })}
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
                onChange={(event) => onChange({ ...form, video_cols: event.target.value })}
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
                onChange={(event) => onChange({ ...form, panel_item_key: event.target.value })}
              />
            </FormField>
          </FormGrid>
          <Button
            size="sm"
            variant="secondary"
            disabled={saving}
            onClick={() => onChange({ ...form, video_rows: "", video_cols: "", panel_item_key: "" })}
          >
            {adminLabels.fairStandItemsClearVideoWall}
          </Button>
        </FormSection>

        <FormActions
          onCancel={requestBack}
          cancelLabel={adminLabels.fairStandItemsBack}
          submitLabel={adminLabels.fairStandItemsSave}
          saving={saving}
        />
      </form>
    </>
  );
}
