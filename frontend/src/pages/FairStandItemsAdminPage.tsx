import React from "react";
import {
  archiveFairStandAdminItemRecord,
  createFairStandAdminItemRecord,
  getFairStandAdminItemRecord,
  listFairStandAdminItemRecords,
  restoreFairStandAdminItemRecord,
  updateFairStandAdminItemRecord,
  type FairStandAdminItemRecord,
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
  FormDirtyHost,
  FormField,
  FormGrid,
  FormModal,
  FormSection,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
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

export function FairStandItemsAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_ITEMS_READ);
  const canCreate = granted.has(FAIR_STAND_ITEMS_CREATE);
  const canUpdate = granted.has(FAIR_STAND_ITEMS_UPDATE);
  const canArchive = granted.has(FAIR_STAND_ITEMS_ARCHIVE);

  const [items, setItems] = React.useState<FairStandAdminItemRecordSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [createForm, setCreateForm] = React.useState<CreateForm | null>(null);
  const [editKey, setEditKey] = React.useState<string | null>(null);
  const [editForm, setEditForm] = React.useState<EditForm | null>(null);
  const [editBaseline, setEditBaseline] = React.useState<EditForm | null>(null);
  const [editLoading, setEditLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [archiveTarget, setArchiveTarget] = React.useState<FairStandAdminItemRecordSummary | null>(null);

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

  const closeCreate = () => setCreateForm(null);
  const closeEdit = () => {
    setEditKey(null);
    setEditForm(null);
    setEditBaseline(null);
  };

  const openEdit = async (row: FairStandAdminItemRecordSummary) => {
    if (!canUpdate) return;
    setSuccess(null);
    setError(null);
    setEditLoading(true);
    setEditKey(row.itemKey);
    try {
      const detail = await getFairStandAdminItemRecord(row.itemKey);
      const form = detailToForm(detail);
      setEditForm(form);
      setEditBaseline(form);
    } catch (detailError) {
      setEditKey(null);
      setError(detailError instanceof Error ? detailError.message : adminLabels.fairStandItemsDetailLoadError);
    } finally {
      setEditLoading(false);
    }
  };

  const saveCreate = async () => {
    if (!canCreate || !createForm) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await createFairStandAdminItemRecord({
        item_key: requireText(createForm.item_key, adminLabels.fairStandItemsFieldItemKey),
        name: requireText(createForm.name, adminLabels.fairStandItemsFieldName),
        item_type: requireText(createForm.item_type, adminLabels.fairStandItemsFieldItemType),
      });
      setCreateForm(null);
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
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
      await updateFairStandAdminItemRecord(editKey, buildUpdatePayload(editForm));
      closeEdit();
      setSuccess(adminLabels.fairStandItemsSaveSuccess);
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandItemsSaveError);
    } finally {
      setSaving(false);
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
          {canUpdate ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                void openEdit(row);
              }}
            >
              {adminLabels.fairStandItemsActionEdit}
            </Button>
          ) : null}
          {canArchive && row.isActive ? (
            <Button size="sm" variant="danger" onClick={() => setArchiveTarget(row)}>
              {adminLabels.fairStandItemsActionArchive}
            </Button>
          ) : null}
          {canArchive && !row.isActive ? (
            <Button
              size="sm"
              onClick={() => {
                void (async () => {
                  try {
                    await restoreFairStandAdminItemRecord(row.itemKey);
                    setSuccess(adminLabels.fairStandItemsSaveSuccess);
                    await load();
                  } catch (restoreError) {
                    setError(
                      restoreError instanceof Error
                        ? restoreError.message
                        : adminLabels.fairStandItemsRestoreError,
                    );
                  }
                })();
              }}
            >
              {adminLabels.fairStandItemsActionRestore}
            </Button>
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
            <Button
              variant="primary"
              onClick={() => {
                setSuccess(null);
                setError(null);
                setCreateForm({ ...emptyCreate });
              }}
            >
              {adminLabels.fairStandItemsCreate}
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandItemsPermissionDenied}</Banner> : null}
      {loading || editLoading ? <LoadingState /> : null}

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

      {createForm ? (
        <FormDirtyHost onClose={closeCreate}>
          <FormDirtyReporter values={createForm} baseline={emptyCreate} />
          <FormModal
            title={adminLabels.fairStandItemsCreateTitle}
            onClose={closeCreate}
            formWidth="narrow"
            footer={
              <>
                <Button variant="secondary" onClick={closeCreate} disabled={saving}>
                  {adminLabels.fairStandItemsCancel}
                </Button>
                <Button
                  variant="primary"
                  loading={saving}
                  onClick={() => {
                    void saveCreate();
                  }}
                >
                  {adminLabels.fairStandItemsSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandItemsSectionIdentity}>
              <FormField
                label={adminLabels.fairStandItemsFieldItemKey}
                htmlFor="fs-item-key"
                hint={adminLabels.fairStandItemsFieldItemKeyHint}
                required
              >
                <TextInput
                  id="fs-item-key"
                  value={createForm.item_key}
                  disabled={saving}
                  onChange={(event) => setCreateForm({ ...createForm, item_key: event.target.value })}
                  required
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldName}
                htmlFor="fs-item-name"
                hint={adminLabels.fairStandItemsFieldNameHint}
                required
              >
                <TextInput
                  id="fs-item-name"
                  value={createForm.name}
                  disabled={saving}
                  onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })}
                  required
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandItemsFieldItemType}
                htmlFor="fs-item-type"
                hint={adminLabels.fairStandItemsFieldItemTypeHint}
                required
              >
                <TextInput
                  id="fs-item-type"
                  value={createForm.item_type}
                  disabled={saving}
                  onChange={(event) => setCreateForm({ ...createForm, item_type: event.target.value })}
                  required
                />
              </FormField>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {editForm && editBaseline && editKey ? (
        <FormDirtyHost onClose={closeEdit}>
          <FormDirtyReporter values={editForm} baseline={editBaseline} />
          <FormModal
            title={adminLabels.fairStandItemsEditTitle}
            onClose={closeEdit}
            size="lg"
            formWidth="wide"
            footer={
              <>
                <Button variant="secondary" onClick={closeEdit} disabled={saving}>
                  {adminLabels.fairStandItemsCancel}
                </Button>
                <Button
                  variant="primary"
                  loading={saving}
                  onClick={() => {
                    void saveEdit();
                  }}
                >
                  {adminLabels.fairStandItemsSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandItemsSectionIdentity}>
              <FormField label={adminLabels.fairStandItemsFieldItemKey} htmlFor="fs-edit-item-key">
                <TextInput id="fs-edit-item-key" value={editKey} readOnly disabled />
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
                    value={editForm.name}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, name: event.target.value })}
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
                    value={editForm.item_type}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, item_type: event.target.value })}
                    required
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldUnit} htmlFor="fs-edit-unit">
                  <TextInput
                    id="fs-edit-unit"
                    value={editForm.unit}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, unit: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldMaterial} htmlFor="fs-edit-material">
                  <TextInput
                    id="fs-edit-material"
                    value={editForm.material}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, material: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldPanelRole} htmlFor="fs-edit-panel-role">
                  <TextInput
                    id="fs-edit-panel-role"
                    value={editForm.panel_role}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, panel_role: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldConnectorType} htmlFor="fs-edit-connector">
                  <TextInput
                    id="fs-edit-connector"
                    value={editForm.connector_type}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, connector_type: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldShape} htmlFor="fs-edit-shape">
                  <TextInput
                    id="fs-edit-shape"
                    value={editForm.shape}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, shape: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldVariant} htmlFor="fs-edit-variant">
                  <TextInput
                    id="fs-edit-variant"
                    value={editForm.variant}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, variant: event.target.value })}
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
                    value={editForm.default_z_cm}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, default_z_cm: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldSnapTarget} htmlFor="fs-edit-snap-target">
                  <TextInput
                    id="fs-edit-snap-target"
                    value={editForm.snap_target_item_type}
                    disabled={saving}
                    onChange={(event) =>
                      setEditForm({ ...editForm, snap_target_item_type: event.target.value })
                    }
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldSnapAnchor} htmlFor="fs-edit-snap-anchor">
                  <TextInput
                    id="fs-edit-snap-anchor"
                    value={editForm.snap_anchor}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, snap_anchor: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldCompositionMode} htmlFor="fs-edit-comp-mode">
                  <TextInput
                    id="fs-edit-comp-mode"
                    value={editForm.composition_mode}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, composition_mode: event.target.value })}
                  />
                </FormField>
              </FormGrid>
              <CheckboxField
                id="fs-edit-is-active"
                label={adminLabels.fairStandItemsFieldIsActive}
                checked={editForm.is_active}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, is_active: checked })}
              />
              <CheckboxField
                id="fs-edit-is-render"
                label={adminLabels.fairStandItemsFieldIsRender}
                hint={adminLabels.fairStandItemsFieldIsRenderHint}
                checked={editForm.is_render}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, is_render: checked })}
              />
              <CheckboxField
                id="fs-edit-preserve-scale"
                label={adminLabels.fairStandItemsFieldPreserveModelScale}
                checked={editForm.preserve_model_scale}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, preserve_model_scale: checked })}
              />
              <CheckboxField
                id="fs-edit-paintable"
                label={adminLabels.fairStandItemsFieldPaintable}
                checked={editForm.paintable}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, paintable: checked })}
              />
              <CheckboxField
                id="fs-edit-accepts-color"
                label={adminLabels.fairStandItemsFieldAcceptsColor}
                checked={editForm.accepts_color}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, accepts_color: checked })}
              />
              <CheckboxField
                id="fs-edit-accepts-image"
                label={adminLabels.fairStandItemsFieldAcceptsImage}
                checked={editForm.accepts_image}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, accepts_image: checked })}
              />
              <CheckboxField
                id="fs-edit-accepts-lightbox"
                label={adminLabels.fairStandItemsFieldAcceptsLightbox}
                checked={editForm.accepts_lightbox}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, accepts_lightbox: checked })}
              />
              <CheckboxField
                id="fs-edit-accepts-glass"
                label={adminLabels.fairStandItemsFieldAcceptsGlass}
                checked={editForm.accepts_glass}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, accepts_glass: checked })}
              />
              <CheckboxField
                id="fs-edit-accepts-mesh"
                label={adminLabels.fairStandItemsFieldAcceptsMesh}
                checked={editForm.accepts_mesh}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, accepts_mesh: checked })}
              />
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionCatalog}>
              <FormGrid columns={2}>
                <FormField label={adminLabels.fairStandItemsFieldCategoryId} htmlFor="fs-edit-category">
                  <TextInput
                    id="fs-edit-category"
                    type="number"
                    value={editForm.category_id}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, category_id: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldCatalogItemIndex} htmlFor="fs-edit-index">
                  <TextInput
                    id="fs-edit-index"
                    type="number"
                    value={editForm.catalog_item_index}
                    disabled={saving}
                    onChange={(event) =>
                      setEditForm({ ...editForm, catalog_item_index: event.target.value })
                    }
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldPreviewId} htmlFor="fs-edit-preview">
                  <TextInput
                    id="fs-edit-preview"
                    type="number"
                    value={editForm.preview_id}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, preview_id: event.target.value })}
                  />
                </FormField>
              </FormGrid>
              <CheckboxField
                id="fs-edit-catalog-visible"
                label={adminLabels.fairStandItemsFieldCatalogVisible}
                hint={adminLabels.fairStandItemsFieldCatalogVisibleHint}
                checked={editForm.catalog_visible}
                disabled={saving}
                onChange={(checked) => setEditForm({ ...editForm, catalog_visible: checked })}
              />
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionDimensions}>
              <FormGrid columns={2}>
                {(
                  [
                    ["width_cm", adminLabels.fairStandItemsFieldWidthCm],
                    ["depth_cm", adminLabels.fairStandItemsFieldDepthCm],
                    ["height_cm", adminLabels.fairStandItemsFieldHeightCm],
                    ["length_cm", adminLabels.fairStandItemsFieldLengthCm],
                    ["thickness_cm", adminLabels.fairStandItemsFieldThicknessCm],
                    ["mount_height_cm", adminLabels.fairStandItemsFieldMountHeightCm],
                    ["wall_gap_cm", adminLabels.fairStandItemsFieldWallGapCm],
                  ] as const
                ).map(([key, label]) => (
                  <FormField key={key} label={label} htmlFor={`fs-edit-${key}`}>
                    <TextInput
                      id={`fs-edit-${key}`}
                      type="number"
                      value={editForm[key]}
                      disabled={saving}
                      onChange={(event) => setEditForm({ ...editForm, [key]: event.target.value })}
                    />
                  </FormField>
                ))}
              </FormGrid>
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionSceneDimensions}>
              <FormGrid columns={2}>
                <FormField label={adminLabels.fairStandItemsFieldWidthCm} htmlFor="fs-edit-scene-width">
                  <TextInput
                    id="fs-edit-scene-width"
                    type="number"
                    value={editForm.scene_width_cm}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, scene_width_cm: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldDepthCm} htmlFor="fs-edit-scene-depth">
                  <TextInput
                    id="fs-edit-scene-depth"
                    type="number"
                    value={editForm.scene_depth_cm}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, scene_depth_cm: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldHeightCm} htmlFor="fs-edit-scene-height">
                  <TextInput
                    id="fs-edit-scene-height"
                    type="number"
                    value={editForm.scene_height_cm}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, scene_height_cm: event.target.value })}
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
                    value={editForm.strip_align}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, strip_align: event.target.value })}
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
                    value={editForm.strip_count}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, strip_count: event.target.value })}
                  />
                </FormField>
              </FormGrid>
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionAssets}>
              {editForm.assets.map((asset, index) => (
                <FormGrid key={`asset-${index}`} columns={2}>
                  <FormField
                    label={adminLabels.fairStandItemsFieldAssetRole}
                    htmlFor={`fs-asset-role-${index}`}
                  >
                    <TextInput
                      id={`fs-asset-role-${index}`}
                      value={asset.asset_role}
                      disabled={saving}
                      onChange={(event) => {
                        const assets = [...editForm.assets];
                        assets[index] = { ...asset, asset_role: event.target.value };
                        setEditForm({ ...editForm, assets });
                      }}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemsFieldRelativePath}
                    htmlFor={`fs-asset-path-${index}`}
                  >
                    <TextInput
                      id={`fs-asset-path-${index}`}
                      value={asset.relative_path}
                      disabled={saving}
                      onChange={(event) => {
                        const assets = [...editForm.assets];
                        assets[index] = { ...asset, relative_path: event.target.value };
                        setEditForm({ ...editForm, assets });
                      }}
                    />
                  </FormField>
                  <CheckboxField
                    id={`fs-asset-active-${index}`}
                    label={adminLabels.fairStandItemsFieldAssetActive}
                    checked={asset.is_active}
                    disabled={saving}
                    onChange={(checked) => {
                      const assets = [...editForm.assets];
                      assets[index] = { ...asset, is_active: checked };
                      setEditForm({ ...editForm, assets });
                    }}
                  />
                  <div>
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={saving}
                      onClick={() =>
                        setEditForm({
                          ...editForm,
                          assets: editForm.assets.filter((_, assetIndex) => assetIndex !== index),
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
                  setEditForm({
                    ...editForm,
                    assets: [...editForm.assets, { asset_role: "", relative_path: "", is_active: true }],
                  })
                }
              >
                {adminLabels.fairStandItemsAddAsset}
              </Button>
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionComponents}>
              {editForm.components.map((component, index) => (
                <FormGrid key={`component-${index}`} columns={2}>
                  <FormField
                    label={adminLabels.fairStandItemsFieldChildItemKey}
                    htmlFor={`fs-comp-child-${index}`}
                  >
                    <TextInput
                      id={`fs-comp-child-${index}`}
                      value={component.child_item_key}
                      disabled={saving}
                      onChange={(event) => {
                        const components = [...editForm.components];
                        components[index] = { ...component, child_item_key: event.target.value };
                        setEditForm({ ...editForm, components });
                      }}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemsFieldQuantity}
                    htmlFor={`fs-comp-qty-${index}`}
                  >
                    <TextInput
                      id={`fs-comp-qty-${index}`}
                      type="number"
                      value={component.quantity}
                      disabled={saving}
                      onChange={(event) => {
                        const components = [...editForm.components];
                        components[index] = { ...component, quantity: event.target.value };
                        setEditForm({ ...editForm, components });
                      }}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemsFieldSortOrder}
                    htmlFor={`fs-comp-sort-${index}`}
                  >
                    <TextInput
                      id={`fs-comp-sort-${index}`}
                      type="number"
                      value={component.sort_order}
                      disabled={saving}
                      onChange={(event) => {
                        const components = [...editForm.components];
                        components[index] = { ...component, sort_order: event.target.value };
                        setEditForm({ ...editForm, components });
                      }}
                    />
                  </FormField>
                  <div>
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={saving}
                      onClick={() =>
                        setEditForm({
                          ...editForm,
                          components: editForm.components.filter((_, componentIndex) => componentIndex !== index),
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
                  setEditForm({
                    ...editForm,
                    components: [
                      ...editForm.components,
                      {
                        child_item_key: "",
                        quantity: "1",
                        sort_order: String(editForm.components.length),
                      },
                    ],
                  })
                }
              >
                {adminLabels.fairStandItemsAddComponent}
              </Button>
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionBodyParts}>
              {editForm.body_parts.map((part, index) => (
                <FormGrid key={`body-${index}`} columns={2}>
                  <FormField label={adminLabels.fairStandItemsFieldBodyRole} htmlFor={`fs-body-role-${index}`}>
                    <TextInput
                      id={`fs-body-role-${index}`}
                      value={part.body_role}
                      disabled={saving}
                      onChange={(event) => {
                        const body_parts = [...editForm.body_parts];
                        body_parts[index] = { ...part, body_role: event.target.value };
                        setEditForm({ ...editForm, body_parts });
                      }}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemsFieldChildItemKey}
                    htmlFor={`fs-body-child-${index}`}
                  >
                    <TextInput
                      id={`fs-body-child-${index}`}
                      value={part.child_item_key}
                      disabled={saving}
                      onChange={(event) => {
                        const body_parts = [...editForm.body_parts];
                        body_parts[index] = { ...part, child_item_key: event.target.value };
                        setEditForm({ ...editForm, body_parts });
                      }}
                    />
                  </FormField>
                  <div>
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={saving}
                      onClick={() =>
                        setEditForm({
                          ...editForm,
                          body_parts: editForm.body_parts.filter((_, partIndex) => partIndex !== index),
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
                  setEditForm({
                    ...editForm,
                    body_parts: [...editForm.body_parts, { body_role: "", child_item_key: "" }],
                  })
                }
              >
                {adminLabels.fairStandItemsAddBodyPart}
              </Button>
            </FormSection>

            <FormSection title={adminLabels.fairStandItemsSectionVideoWall}>
              <FormGrid columns={2}>
                <FormField label={adminLabels.fairStandItemsFieldVideoRows} htmlFor="fs-edit-video-rows">
                  <TextInput
                    id="fs-edit-video-rows"
                    type="number"
                    value={editForm.video_rows}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, video_rows: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldVideoCols} htmlFor="fs-edit-video-cols">
                  <TextInput
                    id="fs-edit-video-cols"
                    type="number"
                    value={editForm.video_cols}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, video_cols: event.target.value })}
                  />
                </FormField>
                <FormField label={adminLabels.fairStandItemsFieldPanelItemKey} htmlFor="fs-edit-panel-key">
                  <TextInput
                    id="fs-edit-panel-key"
                    value={editForm.panel_item_key}
                    disabled={saving}
                    onChange={(event) => setEditForm({ ...editForm, panel_item_key: event.target.value })}
                  />
                </FormField>
              </FormGrid>
              <Button
                size="sm"
                variant="secondary"
                disabled={saving}
                onClick={() =>
                  setEditForm({ ...editForm, video_rows: "", video_cols: "", panel_item_key: "" })
                }
              >
                {adminLabels.fairStandItemsClearVideoWall}
              </Button>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title={adminLabels.fairStandItemsArchiveConfirmTitle}
          message={adminLabels.fairStandItemsArchiveConfirmMessage}
          confirmLabel={adminLabels.fairStandItemsArchiveConfirm}
          cancelLabel={adminLabels.fairStandItemsCancel}
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminItemRecord(archiveTarget.itemKey);
                setArchiveTarget(null);
                setSuccess(adminLabels.fairStandItemsSaveSuccess);
                await load();
              } catch (archiveError) {
                setArchiveTarget(null);
                setError(
                  archiveError instanceof Error
                    ? archiveError.message
                    : adminLabels.fairStandItemsArchiveError,
                );
              }
            })();
          }}
        />
      ) : null}
    </PageShell>
  );
}
