import React from "react";
import {
  archiveFairStandAdminUnit,
  createFairStandAdminUnit,
  listFairStandAdminUnits,
  restoreFairStandAdminUnit,
  updateFairStandAdminUnit,
  type FairStandAdminUnit,
} from "../api/fairStandAdmin";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
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
  FAIR_STAND_CATALOG_ARCHIVE,
  FAIR_STAND_CATALOG_CREATE,
  FAIR_STAND_CATALOG_READ,
  FAIR_STAND_CATALOG_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type UnitForm = { name: string; symbol: string };

const emptyForm = (): UnitForm => ({ name: "", symbol: "" });

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function unitKeyFromName(value: string): string {
  return value
    .trim()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/İ/g, "i")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 64);
}

function requiredMessage(label: string): string {
  return adminLabels.fairStandUnitsRequired.replace("{label}", label);
}

export function FairStandUnitsAdminPage() {
  const granted = getGrantedFairStandAdminPermissions();
  const canRead = granted.has(FAIR_STAND_CATALOG_READ);
  const canCreate = granted.has(FAIR_STAND_CATALOG_CREATE);
  const canUpdate = granted.has(FAIR_STAND_CATALOG_UPDATE);
  const canArchive = granted.has(FAIR_STAND_CATALOG_ARCHIVE);
  const [rows, setRows] = React.useState<FairStandAdminUnit[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<UnitForm | null>(null);
  const [baseline, setBaseline] = React.useState<UnitForm | null>(null);
  const [editing, setEditing] = React.useState<FairStandAdminUnit | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [archiveTarget, setArchiveTarget] = React.useState<FairStandAdminUnit | null>(null);

  const load = React.useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setRows(await listFairStandAdminUnits());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandUnitsLoadError);
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  React.useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    const next = emptyForm();
    setEditing(null);
    setForm(next);
    setBaseline(next);
    setFormError(null);
  }

  function openEdit(row: FairStandAdminUnit) {
    const next = { name: row.name, symbol: row.symbol };
    setEditing(row);
    setForm(next);
    setBaseline(next);
    setFormError(null);
  }

  function closeForm() {
    setForm(null);
    setBaseline(null);
    setEditing(null);
    setFormError(null);
  }

  const columns: UniversalDataTableColumn<FairStandAdminUnit>[] = [
    { key: "unitKey", title: adminLabels.fairStandUnitsColUnitKey, sortable: false, render: (row) => row.unitKey },
    { key: "name", title: adminLabels.fairStandUnitsColName, sortable: false, render: (row) => row.name },
    { key: "symbol", title: adminLabels.fairStandUnitsColSymbol, sortable: false, render: (row) => row.symbol },
    {
      key: "active",
      title: adminLabels.fairStandCatalogColStatus,
      sortable: false,
      render: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive ? adminLabels.fairStandCatalogStatusActive : adminLabels.fairStandCatalogStatusInactive}
        </Badge>
      ),
    },
    {
      key: "actions",
      title: adminLabels.fairStandCatalogColActions,
      sortable: false,
      render: (row) => (
        <TableRowActions>
          {canUpdate ? (
            <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>
              {adminLabels.fairStandUnitsActionEdit}
            </Button>
          ) : null}
          {canArchive && row.isActive ? (
            <Button size="sm" variant="danger" onClick={() => setArchiveTarget(row)}>
              {adminLabels.fairStandCatalogActionArchive}
            </Button>
          ) : null}
          {canArchive && !row.isActive ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                void (async () => {
                  try {
                    await restoreFairStandAdminUnit(row.id);
                    await load();
                  } catch (restoreError) {
                    setError(
                      restoreError instanceof Error ? restoreError.message : adminLabels.fairStandUnitsSaveError,
                    );
                  }
                })();
              }}
            >
              {adminLabels.fairStandCatalogActionRestore}
            </Button>
          ) : null}
        </TableRowActions>
      ),
    },
  ];

  return (
    <PageShell>
      <PageHeader
        title={adminLabels.fairStandUnitsTitle}
        subtitle={adminLabels.fairStandUnitsSubtitle}
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreate}>
              {adminLabels.fairStandUnitsCreate}
            </Button>
          ) : null
        }
      />
      {!canRead ? <Banner variant="info">{adminLabels.fairStandUnitsPermissionDenied}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
      {canRead ? (
        <section>
          <SectionHeader title={adminLabels.fairStandUnitsTitle} />
          {loading ? (
            <LoadingState />
          ) : (
            <UniversalDataTable
              columns={columns}
              items={rows}
              rowKey={(row) => String(row.id)}
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandUnitsEmptyTitle}
                  description={adminLabels.fairStandUnitsEmptyDescription}
                />
              }
            />
          )}
        </section>
      ) : null}

      {form && baseline ? (
        <FormDirtyHost onClose={closeForm}>
          <FormDirtyReporter values={form} baseline={baseline} />
          <FormModal
            title={editing ? adminLabels.fairStandUnitsEditTitle : adminLabels.fairStandUnitsCreateTitle}
            onClose={closeForm}
            formWidth="narrow"
            footer={
              <>
                <Button variant="secondary" onClick={closeForm} disabled={saving}>
                  {adminLabels.fairStandCatalogCancel}
                </Button>
                <Button
                  variant="primary"
                  disabled={saving}
                  onClick={() => {
                    if (saving) return;
                    void (async () => {
                      const name = form.name.trim();
                      const symbol = form.symbol.trim();
                      if (!name) {
                        setFormError(requiredMessage(adminLabels.fairStandUnitsFieldName));
                        return;
                      }
                      if (!symbol) {
                        setFormError(requiredMessage(adminLabels.fairStandUnitsFieldSymbol));
                        return;
                      }
                      setSaving(true);
                      setFormError(null);
                      try {
                        const payload = { name, symbol };
                        if (editing) {
                          await updateFairStandAdminUnit(editing.id, payload);
                        } else {
                          await createFairStandAdminUnit(payload);
                        }
                        closeForm();
                        await load();
                      } catch (saveError) {
                        setFormError(
                          saveError instanceof Error ? saveError.message : adminLabels.fairStandUnitsSaveError,
                        );
                      } finally {
                        setSaving(false);
                      }
                    })();
                  }}
                >
                  {saving ? adminLabels.fairStandItemsSaving : adminLabels.fairStandCatalogSave}
                </Button>
              </>
            }
          >
            {formError ? <Banner variant="error">{formError}</Banner> : null}
            <FormSection title={adminLabels.fairStandUnitsModalSection}>
              <FormGrid columns={2}>
                <FormField label={adminLabels.fairStandUnitsFieldUnitKey} htmlFor="unit-key">
                  <TextInput id="unit-key" value={unitKeyFromName(form.name)} disabled readOnly />
                </FormField>
                <FormField label={adminLabels.fairStandUnitsFieldName} htmlFor="unit-name" required>
                  <TextInput
                    id="unit-name"
                    value={form.name}
                    onChange={(event) => setForm({ ...form, name: event.target.value })}
                    required
                  />
                </FormField>
                <FormField label={adminLabels.fairStandUnitsFieldSymbol} htmlFor="unit-symbol" required>
                  <TextInput
                    id="unit-symbol"
                    value={form.symbol}
                    onChange={(event) => setForm({ ...form, symbol: event.target.value })}
                    required
                  />
                </FormField>
              </FormGrid>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title={adminLabels.fairStandUnitsArchiveTitle}
          message={adminLabels.fairStandUnitsArchiveMessage.replace("{name}", archiveTarget.name)}
          confirmLabel={adminLabels.fairStandCatalogArchiveConfirm}
          variant="danger"
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminUnit(archiveTarget.id);
                setArchiveTarget(null);
                await load();
              } catch (archiveError) {
                setError(archiveError instanceof Error ? archiveError.message : adminLabels.fairStandUnitsSaveError);
                setArchiveTarget(null);
              }
            })();
          }}
        />
      ) : null}
    </PageShell>
  );
}
