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
};

/** Backend SNAP_FACES / SNAP_EDGES ile aynı set. */
const SNAP_FACES = ["front", "back", "top", "bottom", "left", "right"] as const;
const SNAP_EDGES = ["top", "bottom", "left", "right"] as const;

const emptyForm = (): FormState => ({
  key: "",
  display_name: "",
  is_active: true,
  rule_type_id: "",
  face: "",
  edge: "",
  item_type_ids: [],
});

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
      if (mode === "item-types") setRows(await listFairStandAdminItemTypes());
      else if (mode === "rule-types") setRows(await listFairStandAdminRuleTypes());
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
        const payload = { key, display_name, is_active: form.is_active };
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
