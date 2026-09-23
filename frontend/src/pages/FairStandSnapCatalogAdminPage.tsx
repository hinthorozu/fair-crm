import React from "react";
import {
  archiveFairStandAdminFamily,
  archiveFairStandAdminRule,
  archiveFairStandAdminRuleType,
  createFairStandAdminFamily,
  createFairStandAdminRule,
  createFairStandAdminRuleType,
  listFairStandAdminFamilies,
  listFairStandAdminRules,
  listFairStandAdminRuleTypes,
  restoreFairStandAdminFamily,
  restoreFairStandAdminRule,
  restoreFairStandAdminRuleType,
  updateFairStandAdminFamily,
  updateFairStandAdminRule,
  updateFairStandAdminRuleType,
  type FairStandAdminFamily,
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

type Mode = "families" | "rule-types" | "rules";

type Row = FairStandAdminFamily | FairStandAdminRuleType | FairStandAdminRule;

type FormState = {
  code: string;
  display_name: string;
  sort_index: string;
  is_active: boolean;
  rule_type_id: string;
  face: string;
  edge: string;
  mount_mode: string;
};

const emptyForm = (): FormState => ({
  code: "",
  display_name: "",
  sort_index: "0",
  is_active: true,
  rule_type_id: "",
  face: "",
  edge: "",
  mount_mode: "",
});

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function titles(mode: Mode) {
  if (mode === "families") {
    return { title: adminLabels.fairStandFamiliesTitle, subtitle: adminLabels.fairStandFamiliesSubtitle };
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
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<FormState | null>(null);
  const [editing, setEditing] = React.useState<Row | null>(null);
  const { title, subtitle } = titles(mode);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (mode === "families") setRows(await listFairStandAdminFamilies());
      else if (mode === "rule-types") setRows(await listFairStandAdminRuleTypes());
      else {
        const [rules, types] = await Promise.all([
          listFairStandAdminRules(),
          listFairStandAdminRuleTypes(),
        ]);
        setRows(rules);
        setRuleTypes(types);
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
    const next = emptyForm();
    if (mode === "rules") {
      const snap = ruleTypes.find((row) => row.code === "snap") ?? ruleTypes[0];
      next.rule_type_id = snap ? String(snap.id) : "";
    }
    setForm(next);
  };

  const openEdit = (row: Row) => {
    setEditing(row);
    setForm({
      code: row.code,
      display_name: row.displayName,
      sort_index: "sortIndex" in row ? String(row.sortIndex) : "0",
      is_active: row.isActive,
      rule_type_id: "ruleTypeId" in row ? String(row.ruleTypeId) : "",
      face: "face" in row ? String(row.face ?? "") : "",
      edge: "edge" in row ? String(row.edge ?? "") : "",
      mount_mode: "mountMode" in row ? String(row.mountMode ?? "") : "",
    });
  };

  const closeModal = () => {
    setForm(null);
    setEditing(null);
  };

  const save = async () => {
    if (!form) return;
    const code = form.code.trim();
    const display_name = form.display_name.trim();
    if (!code || !display_name) {
      setError("Kod ve ad zorunludur.");
      return;
    }
    try {
      if (mode === "families") {
        const payload = {
          code,
          display_name,
          sort_index: Number(form.sort_index) || 0,
          is_active: form.is_active,
        };
        if (editing) await updateFairStandAdminFamily(editing.id, payload);
        else await createFairStandAdminFamily(payload);
      } else if (mode === "rule-types") {
        const payload = { code, display_name, is_active: form.is_active };
        if (editing) await updateFairStandAdminRuleType(editing.id, payload);
        else await createFairStandAdminRuleType(payload);
      } else {
        const payload = {
          rule_type_id: Number(form.rule_type_id),
          code,
          display_name,
          face: form.face.trim() || null,
          edge: form.edge.trim() || null,
          mount_mode: form.mount_mode.trim() || null,
          sort_index: Number(form.sort_index) || 0,
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
      if (mode === "families") {
        if (row.isActive) await archiveFairStandAdminFamily(row.id);
        else await restoreFairStandAdminFamily(row.id);
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
    { id: "code", header: adminLabels.fairStandSnapCatalogColCode, cell: (row) => row.code },
    { id: "name", header: adminLabels.fairStandSnapCatalogColName, cell: (row) => row.displayName },
    ...(mode === "rules"
      ? [
          {
            id: "type",
            header: adminLabels.fairStandSnapCatalogFieldRuleType,
            cell: (row: Row) => ("ruleTypeCode" in row ? String(row.ruleTypeCode ?? "") : ""),
          },
          {
            id: "mount",
            header: adminLabels.fairStandSnapCatalogFieldMountMode,
            cell: (row: Row) => ("mountMode" in row ? String(row.mountMode ?? "") : ""),
          },
        ]
      : []),
    {
      id: "status",
      header: adminLabels.fairStandSnapCatalogColStatus,
      cell: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive ? adminLabels.fairStandSnapCatalogActive : adminLabels.fairStandSnapCatalogInactive}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: adminLabels.fairStandSnapCatalogColActions,
      cell: (row) => (
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
        code: editing.code,
        display_name: editing.displayName,
        sort_index: "sortIndex" in editing ? String(editing.sortIndex) : "0",
        is_active: editing.isActive,
        rule_type_id: "ruleTypeId" in editing ? String(editing.ruleTypeId) : "",
        face: "face" in editing ? String(editing.face ?? "") : "",
        edge: "edge" in editing ? String(editing.edge ?? "") : "",
        mount_mode: "mountMode" in editing ? String(editing.mountMode ?? "") : "",
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
              <FormField label={adminLabels.fairStandSnapCatalogFieldCode} htmlFor="fs-snap-code">
                <TextInput
                  id="fs-snap-code"
                  value={form.code}
                  onChange={(event) => setForm({ ...form, code: event.target.value })}
                />
              </FormField>
              <FormField label={adminLabels.fairStandSnapCatalogFieldName} htmlFor="fs-snap-name">
                <TextInput
                  id="fs-snap-name"
                  value={form.display_name}
                  onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                />
              </FormField>
              {mode !== "rule-types" ? (
                <FormField label={adminLabels.fairStandSnapCatalogFieldSort} htmlFor="fs-snap-sort">
                  <TextInput
                    id="fs-snap-sort"
                    type="number"
                    value={form.sort_index}
                    onChange={(event) => setForm({ ...form, sort_index: event.target.value })}
                  />
                </FormField>
              ) : null}
              {mode === "rules" ? (
                <>
                  <FormField label={adminLabels.fairStandSnapCatalogFieldRuleType} htmlFor="fs-snap-type">
                    <select
                      id="fs-snap-type"
                      value={form.rule_type_id}
                      onChange={(event) => setForm({ ...form, rule_type_id: event.target.value })}
                    >
                      <option value="">—</option>
                      {ruleTypes.map((type) => (
                        <option key={type.id} value={String(type.id)}>
                          {type.displayName} ({type.code})
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label={adminLabels.fairStandSnapCatalogFieldFace} htmlFor="fs-snap-face">
                    <TextInput
                      id="fs-snap-face"
                      value={form.face}
                      onChange={(event) => setForm({ ...form, face: event.target.value })}
                    />
                  </FormField>
                  <FormField label={adminLabels.fairStandSnapCatalogFieldEdge} htmlFor="fs-snap-edge">
                    <TextInput
                      id="fs-snap-edge"
                      value={form.edge}
                      onChange={(event) => setForm({ ...form, edge: event.target.value })}
                    />
                  </FormField>
                  <FormField label={adminLabels.fairStandSnapCatalogFieldMountMode} htmlFor="fs-snap-mount">
                    <TextInput
                      id="fs-snap-mount"
                      value={form.mount_mode}
                      onChange={(event) => setForm({ ...form, mount_mode: event.target.value })}
                    />
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

export function FairStandFamiliesAdminPage() {
  return <SnapCatalogPage mode="families" />;
}

export function FairStandRuleTypesAdminPage() {
  return <SnapCatalogPage mode="rule-types" />;
}

export function FairStandRulesAdminPage() {
  return <SnapCatalogPage mode="rules" />;
}
