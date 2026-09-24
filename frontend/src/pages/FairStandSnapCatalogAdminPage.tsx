import React from "react";
import {
  archiveFairStandAdminItemType,
  archiveFairStandAdminRule,
  archiveFairStandAdminRuleType,
  createFairStandAdminItemType,
  createFairStandAdminRule,
  createFairStandAdminRuleType,
  listFairStandAdminItemTypes,
  listFairStandAdminRules,
  listFairStandAdminRuleTypes,
  restoreFairStandAdminItemType,
  restoreFairStandAdminRule,
  restoreFairStandAdminRuleType,
  updateFairStandAdminItemType,
  updateFairStandAdminRule,
  updateFairStandAdminRuleType,
  type FairStandAdminItemType,
  type FairStandAdminRule,
  type FairStandAdminRuleType,
} from "../api/fairStandAdmin";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import {
  CheckboxField,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormModal,
  SelectInput,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { TableRowActions } from "../components/ui/TableRowActions";
import { adminLabels } from "../labels/adminLabels";
import {
  FAIR_STAND_ITEMS_ARCHIVE,
  FAIR_STAND_ITEMS_CREATE,
  FAIR_STAND_ITEMS_READ,
  FAIR_STAND_ITEMS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type Mode = "item-types" | "rule-types" | "rules";

type Row = FairStandAdminItemType | FairStandAdminRuleType | FairStandAdminRule;

type FormState = {
  key: string;
  display_name: string;
  is_active: boolean;
  rule_type_id: string;
  face: string;
  edge: string;
  item_type_ids: number[];
  placement: string;
  collision: string;
  move_snap_cm: string;
  magnetic_snap: string;
  allow_side_insert: boolean;
  supports_wall_overlay_mount: boolean;
  wall_capacity: string;
  connection_endpoint: string;
  collision_depth: string;
  endpoint_contact: string;
  boundary_snap: string;
  collision_height: string;
  overlap_with_types: number[];
  ghost_kind: string;
  ghost_renderer: string;
  ghost_opacity: string;
};

/** Backend SNAP_FACES / SNAP_EDGES ile aynı set. */
const SNAP_FACES = ["front", "back", "top", "bottom", "left", "right"] as const;
const SNAP_EDGES = ["top", "bottom", "left", "right"] as const;
/** Backend PLACEMENT / COLLISION / MAGNETIC / CAPACITY / kesit3. */
const ITEM_TYPE_PLACEMENTS = ["wall", "free", "wall-overlay", "top"] as const;
const ITEM_TYPE_COLLISIONS = ["segment", "footprint", "none"] as const;
const ITEM_TYPE_MAGNETIC = ["standard", "none", "short-up-joint"] as const;
const ITEM_TYPE_WALL_CAPACITY = ["include", "exclude"] as const;
const ITEM_TYPE_CONNECTION_ENDPOINT = ["segment", "logical-fixture"] as const;
const ITEM_TYPE_COLLISION_DEPTH = ["physical", "wall-backbone"] as const;
const ITEM_TYPE_ENDPOINT_CONTACT = ["standard", "thin-wall-endpoint"] as const;
const ITEM_TYPE_BOUNDARY_SNAP = ["stand-edge", "wall-inner-face"] as const;
const ITEM_TYPE_COLLISION_HEIGHT = ["full"] as const;

const emptyForm = (): FormState => ({
  key: "",
  display_name: "",
  is_active: true,
  rule_type_id: "",
  face: "",
  edge: "",
  item_type_ids: [],
  placement: "wall",
  collision: "segment",
  move_snap_cm: "50",
  magnetic_snap: "standard",
  allow_side_insert: true,
  supports_wall_overlay_mount: true,
  wall_capacity: "include",
  connection_endpoint: "segment",
  collision_depth: "physical",
  endpoint_contact: "standard",
  boundary_snap: "stand-edge",
  collision_height: "full",
  overlap_with_types: [],
  ghost_kind: "silhouette",
  ghost_renderer: "module-silhouette",
  ghost_opacity: "0.38",
});

function itemTypeBehaviorFromRow(row: Row): Pick<
  FormState,
  | "placement"
  | "collision"
  | "move_snap_cm"
  | "magnetic_snap"
  | "allow_side_insert"
  | "supports_wall_overlay_mount"
  | "wall_capacity"
  | "connection_endpoint"
  | "collision_depth"
  | "endpoint_contact"
  | "boundary_snap"
  | "collision_height"
  | "overlap_with_types"
  | "ghost_kind"
  | "ghost_renderer"
  | "ghost_opacity"
> {
  if (!("placement" in row)) {
    return {
      placement: "wall",
      collision: "segment",
      move_snap_cm: "50",
      magnetic_snap: "standard",
      allow_side_insert: true,
      supports_wall_overlay_mount: true,
      wall_capacity: "include",
      connection_endpoint: "segment",
      collision_depth: "physical",
      endpoint_contact: "standard",
      boundary_snap: "stand-edge",
      collision_height: "full",
      overlap_with_types: [],
      ghost_kind: "silhouette",
      ghost_renderer: "module-silhouette",
      ghost_opacity: "0.38",
    };
  }
  const typed = row as FairStandAdminItemType;
  return {
    placement: typed.placement || "wall",
    collision: typed.collision || "segment",
    move_snap_cm: String(typed.moveSnapCm ?? 50),
    magnetic_snap: typed.magneticSnap || "standard",
    allow_side_insert: typed.allowSideInsert !== false,
    supports_wall_overlay_mount: typed.supportsWallOverlayMount !== false,
    wall_capacity: typed.wallCapacity || "include",
    connection_endpoint: typed.connectionEndpoint || "segment",
    collision_depth: typed.collisionDepth || "physical",
    endpoint_contact: typed.endpointContact || "standard",
    boundary_snap: typed.boundarySnap || "stand-edge",
    collision_height: typed.collisionHeight || "full",
    overlap_with_types: [...(typed.overlapItemTypeIds ?? [])],
    ghost_kind: typed.ghost?.kind || "silhouette",
    ghost_renderer: typed.ghost?.renderer || "module-silhouette",
    ghost_opacity: String(typed.ghost?.opacity ?? 0.38),
  };
}

/** Ad → key slug (item key gibi; backend ile aynı fikir). */
function slugifyKey(value: string): string {
  return value
    .trim()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/İ/g, "i")
    .toLocaleLowerCase("en-US")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function titles(mode: Mode) {
  if (mode === "item-types") {
    return { title: adminLabels.fairStandItemTypesTitle, subtitle: adminLabels.fairStandItemTypesSubtitle };
  }
  if (mode === "rule-types") {
    return { title: adminLabels.fairStandRuleTypesTitle, subtitle: adminLabels.fairStandRuleTypesSubtitle };
  }
  return { title: adminLabels.fairStandRulesTitle, subtitle: adminLabels.fairStandRulesSubtitle };
}

function SnapCatalogPage({ mode }: { mode: Mode }) {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_ITEMS_READ);
  const canCreate = granted.has(FAIR_STAND_ITEMS_CREATE);
  const canUpdate = granted.has(FAIR_STAND_ITEMS_UPDATE);
  const canArchive = granted.has(FAIR_STAND_ITEMS_ARCHIVE);
  const [rows, setRows] = React.useState<Row[]>([]);
  const [ruleTypes, setRuleTypes] = React.useState<FairStandAdminRuleType[]>([]);
  const [itemTypes, setItemTypes] = React.useState<FairStandAdminItemType[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<FormState | null>(null);
  const [editing, setEditing] = React.useState<Row | null>(null);
  const [keyManual, setKeyManual] = React.useState(false);
  const { title, subtitle } = titles(mode);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (mode === "item-types") {
        const itemTypeRows = await listFairStandAdminItemTypes();
        setRows(itemTypeRows);
        setItemTypes(itemTypeRows.filter((row) => row.isActive));
      } else if (mode === "rule-types") setRows(await listFairStandAdminRuleTypes());
      else {
        const [rules, types, itemTypeRows] = await Promise.all([
          listFairStandAdminRules(),
          listFairStandAdminRuleTypes(),
          listFairStandAdminItemTypes(),
        ]);
        setRows(rules);
        setRuleTypes(types);
        setItemTypes(itemTypeRows.filter((row) => row.isActive));
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandSnapCatalogLoadError);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const openCreate = () => {
    setEditing(null);
    setKeyManual(false);
    const next = emptyForm();
    if (mode === "rules") {
      const snap = ruleTypes.find((row) => row.key === "snap") ?? ruleTypes[0];
      next.rule_type_id = snap ? String(snap.id) : "";
    }
    setForm(next);
  };

  const openEdit = (row: Row) => {
    setEditing(row);
    setKeyManual(true);
    setForm({
      key: row.key,
      display_name: row.displayName,
      is_active: row.isActive,
      rule_type_id: "ruleTypeId" in row ? String(row.ruleTypeId) : "",
      face: "face" in row ? String(row.face ?? "") : "",
      edge: "edge" in row ? String(row.edge ?? "") : "",
      item_type_ids: "itemTypeIds" in row ? [...(row.itemTypeIds ?? [])] : [],
      ...itemTypeBehaviorFromRow(row),
    });
  };

  const closeModal = () => {
    setForm(null);
    setEditing(null);
    setKeyManual(false);
  };

  const save = async () => {
    if (!form) return;
    const display_name = form.display_name.trim();
    const key = form.key.trim() || slugifyKey(display_name);
    if (!display_name) {
      setError("Ad zorunludur.");
      return;
    }
    if (!key) {
      setError("Key zorunludur.");
      return;
    }
    try {
      if (mode === "item-types") {
        const moveSnapCm = Number(form.move_snap_cm);
        if (!ITEM_TYPE_PLACEMENTS.includes(form.placement as (typeof ITEM_TYPE_PLACEMENTS)[number])) {
          setError(adminLabels.fairStandItemTypesPlacementRequired);
          return;
        }
        if (!ITEM_TYPE_COLLISIONS.includes(form.collision as (typeof ITEM_TYPE_COLLISIONS)[number])) {
          setError(adminLabels.fairStandItemTypesCollisionRequired);
          return;
        }
        if (!Number.isFinite(moveSnapCm) || moveSnapCm <= 0) {
          setError(adminLabels.fairStandItemTypesMoveSnapRequired);
          return;
        }
        if (!ITEM_TYPE_MAGNETIC.includes(form.magnetic_snap as (typeof ITEM_TYPE_MAGNETIC)[number])) {
          setError(adminLabels.fairStandItemTypesMagneticRequired);
          return;
        }
        if (!ITEM_TYPE_WALL_CAPACITY.includes(form.wall_capacity as (typeof ITEM_TYPE_WALL_CAPACITY)[number])) {
          setError(adminLabels.fairStandItemTypesWallCapacityRequired);
          return;
        }
        if (
          !ITEM_TYPE_CONNECTION_ENDPOINT.includes(
            form.connection_endpoint as (typeof ITEM_TYPE_CONNECTION_ENDPOINT)[number],
          )
        ) {
          setError(adminLabels.fairStandItemTypesConnectionEndpointRequired);
          return;
        }
        if (
          !ITEM_TYPE_COLLISION_DEPTH.includes(
            form.collision_depth as (typeof ITEM_TYPE_COLLISION_DEPTH)[number],
          )
        ) {
          setError(adminLabels.fairStandItemTypesCollisionDepthRequired);
          return;
        }
        if (
          !ITEM_TYPE_ENDPOINT_CONTACT.includes(
            form.endpoint_contact as (typeof ITEM_TYPE_ENDPOINT_CONTACT)[number],
          )
        ) {
          setError(adminLabels.fairStandItemTypesEndpointContactRequired);
          return;
        }
        if (
          !ITEM_TYPE_BOUNDARY_SNAP.includes(
            form.boundary_snap as (typeof ITEM_TYPE_BOUNDARY_SNAP)[number],
          )
        ) {
          setError(adminLabels.fairStandItemTypesBoundarySnapRequired);
          return;
        }
        if (
          !ITEM_TYPE_COLLISION_HEIGHT.includes(
            form.collision_height as (typeof ITEM_TYPE_COLLISION_HEIGHT)[number],
          )
        ) {
          setError(adminLabels.fairStandItemTypesCollisionHeightRequired);
          return;
        }
        const ghostOpacity = Number(form.ghost_opacity);
        if (!Number.isFinite(ghostOpacity) || ghostOpacity < 0 || ghostOpacity > 1) {
          setError(adminLabels.fairStandItemTypesGhostOpacityRequired);
          return;
        }
        if (!form.ghost_kind.trim() || !form.ghost_renderer.trim()) {
          setError(adminLabels.fairStandItemTypesGhostRequired);
          return;
        }
        const payload = {
          key,
          display_name,
          is_active: form.is_active,
          placement: form.placement,
          collision: form.collision,
          move_snap_cm: Math.trunc(moveSnapCm),
          magnetic_snap: form.magnetic_snap,
          allow_side_insert: form.allow_side_insert,
          supports_wall_overlay_mount: form.supports_wall_overlay_mount,
          wall_capacity: form.wall_capacity,
          connection_endpoint: form.connection_endpoint,
          collision_depth: form.collision_depth,
          endpoint_contact: form.endpoint_contact,
          boundary_snap: form.boundary_snap,
          collision_height: form.collision_height,
          overlap_item_type_ids: form.overlap_with_types,
          ghost_kind: form.ghost_kind.trim(),
          ghost_renderer: form.ghost_renderer.trim(),
          ghost_opacity: ghostOpacity,
        };
        if (editing) await updateFairStandAdminItemType(editing.id, payload);
        else await createFairStandAdminItemType(payload);
      } else if (mode === "rule-types") {
        const payload = { key, display_name, is_active: form.is_active };
        if (editing) await updateFairStandAdminRuleType(editing.id, payload);
        else await createFairStandAdminRuleType(payload);
      } else {
        const payload = {
          rule_type_id: Number(form.rule_type_id),
          key,
          display_name,
          face: form.face.trim() || null,
          edge: form.edge.trim() || null,
          item_type_ids: form.item_type_ids,
          is_active: form.is_active,
        };
        if (editing) await updateFairStandAdminRule(editing.id, payload);
        else await createFairStandAdminRule(payload);
      }
      closeModal();
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : adminLabels.fairStandSnapCatalogLoadError);
    }
  };

  const toggleActive = async (row: Row) => {
    try {
      if (mode === "item-types") {
        if (row.isActive) await archiveFairStandAdminItemType(row.id);
        else await restoreFairStandAdminItemType(row.id);
      } else if (mode === "rule-types") {
        if (row.isActive) await archiveFairStandAdminRuleType(row.id);
        else await restoreFairStandAdminRuleType(row.id);
      } else if (row.isActive) await archiveFairStandAdminRule(row.id);
      else await restoreFairStandAdminRule(row.id);
      await load();
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : adminLabels.fairStandSnapCatalogLoadError);
    }
  };

  const columns: UniversalDataTableColumn<Row>[] = [
    {
      key: "key",
      title: adminLabels.fairStandSnapCatalogColCode,
      sortable: false,
      render: (row) => row.key,
    },
    {
      key: "name",
      title: adminLabels.fairStandSnapCatalogColName,
      sortable: false,
      render: (row) => row.displayName,
    },
    ...(mode === "item-types"
      ? [
          {
            key: "placement",
            title: adminLabels.fairStandItemTypesColPlacement,
            sortable: false,
            render: (row: Row) => ("placement" in row ? String(row.placement ?? "") : ""),
          },
          {
            key: "collision",
            title: adminLabels.fairStandItemTypesColCollision,
            sortable: false,
            render: (row: Row) => ("collision" in row ? String(row.collision ?? "") : ""),
          },
          {
            key: "moveSnapCm",
            title: adminLabels.fairStandItemTypesColMoveSnap,
            sortable: false,
            render: (row: Row) => ("moveSnapCm" in row ? String(row.moveSnapCm ?? "") : ""),
          },
        ]
      : []),
    ...(mode === "rules"
      ? [
          {
            key: "type",
            title: adminLabels.fairStandSnapCatalogFieldRuleType,
            sortable: false,
            render: (row: Row) => ("ruleTypeKey" in row ? String(row.ruleTypeKey ?? "") : ""),
          },
          {
            key: "face",
            title: adminLabels.fairStandSnapCatalogFieldFace,
            sortable: false,
            render: (row: Row) => ("face" in row ? String(row.face ?? "") : ""),
          },
          {
            key: "edge",
            title: adminLabels.fairStandSnapCatalogFieldEdge,
            sortable: false,
            render: (row: Row) => ("edge" in row ? String(row.edge ?? "") : ""),
          },
          {
            key: "itemTypes",
            title: adminLabels.fairStandSnapCatalogFieldItemTypes,
            sortable: false,
            render: (row: Row) =>
              "itemTypeKeys" in row ? (row.itemTypeKeys?.length ? row.itemTypeKeys.join(", ") : "—") : "",
          },
        ]
      : []),
    {
      key: "status",
      title: adminLabels.fairStandSnapCatalogColStatus,
      sortable: false,
      render: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive ? adminLabels.fairStandSnapCatalogActive : adminLabels.fairStandSnapCatalogInactive}
        </Badge>
      ),
    },
    {
      key: "actions",
      title: adminLabels.fairStandSnapCatalogColActions,
      sortable: false,
      render: (row) => (
        <TableRowActions>
          {canUpdate ? (
            <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>
              {adminLabels.fairStandSnapCatalogEdit}
            </Button>
          ) : null}
          {canArchive ? (
            <Button
              size="sm"
              variant={row.isActive ? "danger" : "secondary"}
              onClick={() => void toggleActive(row)}
            >
              {row.isActive
                ? adminLabels.fairStandSnapCatalogArchive
                : adminLabels.fairStandSnapCatalogRestore}
            </Button>
          ) : null}
        </TableRowActions>
      ),
    },
  ];

  const baseline = editing
    ? {
        key: editing.key,
        display_name: editing.displayName,
        is_active: editing.isActive,
        rule_type_id: "ruleTypeId" in editing ? String(editing.ruleTypeId) : "",
        face: "face" in editing ? String(editing.face ?? "") : "",
        edge: "edge" in editing ? String(editing.edge ?? "") : "",
        item_type_ids: "itemTypeIds" in editing ? [...(editing.itemTypeIds ?? [])] : [],
        ...itemTypeBehaviorFromRow(editing),
      }
    : emptyForm();

  return (
    <PageShell>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreate}>
              {adminLabels.fairStandSnapCatalogCreate}
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandSnapCatalogPermissionDenied}</Banner> : null}
      {loading ? <LoadingState /> : null}
      {canRead && !loading ? (
        <UniversalDataTable
          items={rows}
          columns={columns}
          rowKey={(row) => String(row.id)}
          emptyState={<EmptyState title={adminLabels.fairStandSnapCatalogEmpty} />}
          toolbar={
            <Button variant="secondary" onClick={() => void load()}>
              {adminLabels.fairStandSnapCatalogRefresh}
            </Button>
          }
        />
      ) : null}
      {form ? (
        <FormDirtyHost onClose={closeModal}>
          <FormDirtyReporter values={form} baseline={baseline} />
          <FormModal
            title={editing ? adminLabels.fairStandSnapCatalogEdit : adminLabels.fairStandSnapCatalogCreate}
            onClose={closeModal}
            footer={
              <>
                <Button variant="secondary" onClick={closeModal}>
                  İptal
                </Button>
                <Button variant="primary" onClick={() => void save()}>
                  Kaydet
                </Button>
              </>
            }
          >
            <FormGrid columns={2}>
              <FormField label={adminLabels.fairStandSnapCatalogFieldName} htmlFor="fs-snap-name">
                <TextInput
                  id="fs-snap-name"
                  value={form.display_name}
                  onChange={(event) => {
                    const display_name = event.target.value;
                    setForm({
                      ...form,
                      display_name,
                      key: keyManual ? form.key : slugifyKey(display_name),
                    });
                  }}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandSnapCatalogFieldCode}
                htmlFor="fs-snap-key"
                hint={adminLabels.fairStandSnapCatalogFieldCodeHint}
              >
                <TextInput
                  id="fs-snap-key"
                  value={form.key}
                  onChange={(event) => {
                    setKeyManual(true);
                    setForm({ ...form, key: event.target.value });
                  }}
                />
              </FormField>
              {mode === "item-types" ? (
                <>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldPlacement}
                    htmlFor="fs-item-type-placement"
                    hint={adminLabels.fairStandItemTypesFieldPlacementHint}
                  >
                    <SelectInput
                      id="fs-item-type-placement"
                      value={form.placement}
                      onChange={(event) => setForm({ ...form, placement: event.target.value })}
                    >
                      <option value="wall">{adminLabels.fairStandItemTypesOptPlacementWall}</option>
                      <option value="free">{adminLabels.fairStandItemTypesOptPlacementFree}</option>
                      <option value="wall-overlay">{adminLabels.fairStandItemTypesOptPlacementOverlay}</option>
                      <option value="top">{adminLabels.fairStandItemTypesOptPlacementTop}</option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldCollision}
                    htmlFor="fs-item-type-collision"
                    hint={adminLabels.fairStandItemTypesFieldCollisionHint}
                  >
                    <SelectInput
                      id="fs-item-type-collision"
                      value={form.collision}
                      onChange={(event) => setForm({ ...form, collision: event.target.value })}
                    >
                      <option value="segment">{adminLabels.fairStandItemTypesOptCollisionSegment}</option>
                      <option value="footprint">{adminLabels.fairStandItemTypesOptCollisionFootprint}</option>
                      <option value="none">{adminLabels.fairStandItemTypesOptCollisionNone}</option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldMoveSnap}
                    htmlFor="fs-item-type-move-snap"
                    hint={adminLabels.fairStandItemTypesFieldMoveSnapHint}
                  >
                    <TextInput
                      id="fs-item-type-move-snap"
                      type="number"
                      min={1}
                      step={1}
                      value={form.move_snap_cm}
                      onChange={(event) => setForm({ ...form, move_snap_cm: event.target.value })}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldMagnetic}
                    htmlFor="fs-item-type-magnetic"
                    hint={adminLabels.fairStandItemTypesFieldMagneticHint}
                  >
                    <SelectInput
                      id="fs-item-type-magnetic"
                      value={form.magnetic_snap}
                      onChange={(event) => setForm({ ...form, magnetic_snap: event.target.value })}
                    >
                      <option value="standard">{adminLabels.fairStandItemTypesOptMagneticStandard}</option>
                      <option value="none">{adminLabels.fairStandItemTypesOptMagneticNone}</option>
                      <option value="short-up-joint">{adminLabels.fairStandItemTypesOptMagneticShortUp}</option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldWallCapacity}
                    htmlFor="fs-item-type-wall-capacity"
                    hint={adminLabels.fairStandItemTypesFieldWallCapacityHint}
                  >
                    <SelectInput
                      id="fs-item-type-wall-capacity"
                      value={form.wall_capacity}
                      onChange={(event) => setForm({ ...form, wall_capacity: event.target.value })}
                    >
                      <option value="include">{adminLabels.fairStandItemTypesOptCapacityInclude}</option>
                      <option value="exclude">{adminLabels.fairStandItemTypesOptCapacityExclude}</option>
                    </SelectInput>
                  </FormField>
                  <CheckboxField
                    id="fs-item-type-allow-side"
                    label={adminLabels.fairStandItemTypesFieldAllowSide}
                    hint={adminLabels.fairStandItemTypesFieldAllowSideHint}
                    checked={form.allow_side_insert}
                    onChange={(checked: boolean) => setForm({ ...form, allow_side_insert: checked })}
                  />
                  <CheckboxField
                    id="fs-item-type-overlay-mount"
                    label={adminLabels.fairStandItemTypesFieldOverlayMount}
                    hint={adminLabels.fairStandItemTypesFieldOverlayMountHint}
                    checked={form.supports_wall_overlay_mount}
                    onChange={(checked: boolean) =>
                      setForm({ ...form, supports_wall_overlay_mount: checked })
                    }
                  />
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldConnectionEndpoint}
                    htmlFor="fs-item-type-connection-endpoint"
                    hint={adminLabels.fairStandItemTypesFieldConnectionEndpointHint}
                  >
                    <SelectInput
                      id="fs-item-type-connection-endpoint"
                      value={form.connection_endpoint}
                      onChange={(event) =>
                        setForm({ ...form, connection_endpoint: event.target.value })
                      }
                    >
                      <option value="segment">{adminLabels.fairStandItemTypesOptEndpointSegment}</option>
                      <option value="logical-fixture">
                        {adminLabels.fairStandItemTypesOptEndpointLogical}
                      </option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldCollisionDepth}
                    htmlFor="fs-item-type-collision-depth"
                    hint={adminLabels.fairStandItemTypesFieldCollisionDepthHint}
                  >
                    <SelectInput
                      id="fs-item-type-collision-depth"
                      value={form.collision_depth}
                      onChange={(event) =>
                        setForm({ ...form, collision_depth: event.target.value })
                      }
                    >
                      <option value="physical">{adminLabels.fairStandItemTypesOptDepthPhysical}</option>
                      <option value="wall-backbone">
                        {adminLabels.fairStandItemTypesOptDepthBackbone}
                      </option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldEndpointContact}
                    htmlFor="fs-item-type-endpoint-contact"
                    hint={adminLabels.fairStandItemTypesFieldEndpointContactHint}
                  >
                    <SelectInput
                      id="fs-item-type-endpoint-contact"
                      value={form.endpoint_contact}
                      onChange={(event) =>
                        setForm({ ...form, endpoint_contact: event.target.value })
                      }
                    >
                      <option value="standard">{adminLabels.fairStandItemTypesOptContactStandard}</option>
                      <option value="thin-wall-endpoint">
                        {adminLabels.fairStandItemTypesOptContactThin}
                      </option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldBoundarySnap}
                    htmlFor="fs-item-type-boundary-snap"
                    hint={adminLabels.fairStandItemTypesFieldBoundarySnapHint}
                  >
                    <SelectInput
                      id="fs-item-type-boundary-snap"
                      value={form.boundary_snap}
                      onChange={(event) =>
                        setForm({ ...form, boundary_snap: event.target.value })
                      }
                    >
                      <option value="stand-edge">{adminLabels.fairStandItemTypesOptBoundaryStand}</option>
                      <option value="wall-inner-face">
                        {adminLabels.fairStandItemTypesOptBoundaryInner}
                      </option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldCollisionHeight}
                    htmlFor="fs-item-type-collision-height"
                    hint={adminLabels.fairStandItemTypesFieldCollisionHeightHint}
                  >
                    <SelectInput
                      id="fs-item-type-collision-height"
                      value={form.collision_height}
                      onChange={(event) =>
                        setForm({ ...form, collision_height: event.target.value })
                      }
                    >
                      <option value="full">{adminLabels.fairStandItemTypesOptHeightFull}</option>
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldOverlap}
                    htmlFor="fs-item-type-overlap"
                    hint={adminLabels.fairStandItemTypesFieldOverlapHint}
                  >
                    <div id="fs-item-type-overlap" style={{ display: "grid", gap: 6 }}>
                      {itemTypes
                        .filter((itemType) => !(editing && "id" in editing && itemType.id === editing.id))
                        .map((itemType) => {
                          const checked = form.overlap_with_types.includes(itemType.id);
                          return (
                            <CheckboxField
                              key={itemType.id}
                              id={`fs-item-type-overlap-${itemType.id}`}
                              label={`${itemType.displayName} (${itemType.key})`}
                              checked={checked}
                              onChange={(next: boolean) =>
                                setForm({
                                  ...form,
                                  overlap_with_types: next
                                    ? [...form.overlap_with_types, itemType.id]
                                    : form.overlap_with_types.filter((id) => id !== itemType.id),
                                })
                              }
                            />
                          );
                        })}
                    </div>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldGhostKind}
                    htmlFor="fs-item-type-ghost-kind"
                    hint={adminLabels.fairStandItemTypesFieldGhostKindHint}
                  >
                    <TextInput
                      id="fs-item-type-ghost-kind"
                      value={form.ghost_kind}
                      onChange={(event) => setForm({ ...form, ghost_kind: event.target.value })}
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldGhostRenderer}
                    htmlFor="fs-item-type-ghost-renderer"
                    hint={adminLabels.fairStandItemTypesFieldGhostRendererHint}
                  >
                    <TextInput
                      id="fs-item-type-ghost-renderer"
                      value={form.ghost_renderer}
                      onChange={(event) =>
                        setForm({ ...form, ghost_renderer: event.target.value })
                      }
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandItemTypesFieldGhostOpacity}
                    htmlFor="fs-item-type-ghost-opacity"
                    hint={adminLabels.fairStandItemTypesFieldGhostOpacityHint}
                  >
                    <TextInput
                      id="fs-item-type-ghost-opacity"
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={form.ghost_opacity}
                      onChange={(event) =>
                        setForm({ ...form, ghost_opacity: event.target.value })
                      }
                    />
                  </FormField>
                </>
              ) : null}
              {mode === "rules" ? (
                <>
                  <FormField label={adminLabels.fairStandSnapCatalogFieldRuleType} htmlFor="fs-snap-type">
                    <SelectInput
                      id="fs-snap-type"
                      value={form.rule_type_id}
                      onChange={(event) => setForm({ ...form, rule_type_id: event.target.value })}
                    >
                      <option value="">—</option>
                      {ruleTypes.map((type) => (
                        <option key={type.id} value={String(type.id)}>
                          {type.displayName} ({type.key})
                        </option>
                      ))}
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandSnapCatalogFieldFace}
                    htmlFor="fs-snap-face"
                    hint={adminLabels.fairStandSnapCatalogFieldFaceHint}
                  >
                    <SelectInput
                      id="fs-snap-face"
                      value={form.face}
                      onChange={(event) => setForm({ ...form, face: event.target.value })}
                    >
                      <option value="">{adminLabels.fairStandSnapCatalogSelectEmpty}</option>
                      {SNAP_FACES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandSnapCatalogFieldEdge}
                    htmlFor="fs-snap-edge"
                    hint={adminLabels.fairStandSnapCatalogFieldEdgeHint}
                  >
                    <SelectInput
                      id="fs-snap-edge"
                      value={form.edge}
                      onChange={(event) => setForm({ ...form, edge: event.target.value })}
                    >
                      <option value="">{adminLabels.fairStandSnapCatalogSelectEmpty}</option>
                      {SNAP_EDGES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </SelectInput>
                  </FormField>
                  <FormField
                    label={adminLabels.fairStandSnapCatalogFieldItemTypes}
                    htmlFor="fs-snap-item-types"
                    hint={adminLabels.fairStandSnapCatalogFieldItemTypesHint}
                    fullWidth
                  >
                    <div id="fs-snap-item-types" style={{ display: "grid", gap: 8 }}>
                      {itemTypes.map((itemType) => {
                        const checked = form.item_type_ids.includes(itemType.id);
                        return (
                          <CheckboxField
                            key={itemType.id}
                            id={`fs-snap-item-type-${itemType.id}`}
                            label={`${itemType.displayName} (${itemType.key})`}
                            checked={checked}
                            onChange={(nextChecked: boolean) => {
                              setForm({
                                ...form,
                                item_type_ids: nextChecked
                                  ? [...form.item_type_ids, itemType.id]
                                  : form.item_type_ids.filter((id) => id !== itemType.id),
                              });
                            }}
                          />
                        );
                      })}
                    </div>
                  </FormField>
                </>
              ) : null}
              <CheckboxField
                id="fs-snap-active"
                label={adminLabels.fairStandSnapCatalogFieldActive}
                checked={form.is_active}
                onChange={(checked: boolean) => setForm({ ...form, is_active: checked })}
              />
            </FormGrid>
          </FormModal>
        </FormDirtyHost>
      ) : null}
    </PageShell>
  );
}

export function FairStandItemTypesAdminPage() {
  return <SnapCatalogPage mode="item-types" />;
}

/** @deprecated Use FairStandItemTypesAdminPage */
export function FairStandFamiliesAdminPage() {
  return <FairStandItemTypesAdminPage />;
}

export function FairStandRuleTypesAdminPage() {
  return <SnapCatalogPage mode="rule-types" />;
}

export function FairStandRulesAdminPage() {
  return <SnapCatalogPage mode="rules" />;
}
