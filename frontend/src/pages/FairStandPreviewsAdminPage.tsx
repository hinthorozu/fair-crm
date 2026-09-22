import React from "react";
import {
  archiveFairStandAdminPreview,
  createFairStandAdminPreview,
  listFairStandAdminPreviews,
  restoreFairStandAdminPreview,
  updateFairStandAdminPreview,
  type FairStandAdminPreview,
} from "../api/fairStandAdmin";
import { FairStandCatalogLivePreview } from "../components/fairStand/FairStandCatalogLivePreview";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  CheckboxField,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormModal,
  FormSection,
  TextareaInput,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  FAIR_STAND_PREVIEWS_ARCHIVE,
  FAIR_STAND_PREVIEWS_CREATE,
  FAIR_STAND_PREVIEWS_READ,
  FAIR_STAND_PREVIEWS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type PreviewForm = {
  display_name: string;
  markup: string;
  css_code: string;
  sort_index: string;
  is_active: boolean;
};

const emptyPreview: PreviewForm = {
  display_name: "",
  markup: "<div class=\"module-drag-shelf\" data-preview-width></div>",
  css_code: ".module-drag-shelf { height: 8px; }",
  sort_index: "1",
  is_active: true,
};

function matchesPreviewSearch(row: FairStandAdminPreview, search: string): boolean {
  const q = search.trim().toLocaleLowerCase("tr-TR");
  if (!q) return true;
  return (
    row.displayName.toLocaleLowerCase("tr-TR").includes(q) ||
    String(row.id).includes(q) ||
    String(row.sortIndex).includes(q)
  );
}

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

export function FairStandPreviewsAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_PREVIEWS_READ);
  const canCreate = granted.has(FAIR_STAND_PREVIEWS_CREATE);
  const canUpdate = granted.has(FAIR_STAND_PREVIEWS_UPDATE);
  const canArchive = granted.has(FAIR_STAND_PREVIEWS_ARCHIVE);
  const [previews, setPreviews] = React.useState<FairStandAdminPreview[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [form, setForm] = React.useState<PreviewForm | null>(null);
  const [editing, setEditing] = React.useState<FairStandAdminPreview | null>(null);
  const [archiveTarget, setArchiveTarget] = React.useState<FairStandAdminPreview | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPreviews(await listFairStandAdminPreviews());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandPreviewsLoadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const closeModal = React.useCallback(() => {
    setForm(null);
    setEditing(null);
  }, []);

  const openEdit = (row: FairStandAdminPreview) => {
    setEditing(row);
    setForm({
      display_name: row.displayName,
      markup: row.markup,
      css_code: row.cssCode,
      sort_index: String(row.sortIndex),
      is_active: row.isActive,
    });
  };

  const filteredPreviews = React.useMemo(
    () => previews.filter((row) => matchesPreviewSearch(row, search)),
    [previews, search],
  );

  const columns: UniversalDataTableColumn<FairStandAdminPreview>[] = [
    { key: "id", title: adminLabels.fairStandPreviewsColId, sortable: false, render: (row) => String(row.id) },
    { key: "name", title: adminLabels.fairStandPreviewsColName, sortable: false, render: (row) => row.displayName },
    {
      key: "index",
      title: adminLabels.fairStandPreviewsColIndex,
      sortable: false,
      render: (row) => String(row.sortIndex),
    },
    {
      key: "active",
      title: adminLabels.fairStandPreviewsColStatus,
      sortable: false,
      render: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive
            ? adminLabels.fairStandPreviewsStatusActive
            : adminLabels.fairStandPreviewsStatusInactive}
        </Badge>
      ),
    },
    {
      key: "live",
      title: adminLabels.fairStandPreviewsColLive,
      sortable: false,
      render: (row) => <FairStandCatalogLivePreview definition={row} />,
    },
    {
      key: "actions",
      title: adminLabels.fairStandPreviewsColActions,
      sortable: false,
      render: (row) => (
        <TableRowActions>
          {canUpdate ? (
            <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>
              {adminLabels.fairStandPreviewsActionEdit}
            </Button>
          ) : null}
          {canArchive && row.isActive ? (
            <Button size="sm" variant="danger" onClick={() => setArchiveTarget(row)}>
              {adminLabels.fairStandPreviewsActionArchive}
            </Button>
          ) : null}
          {canArchive && !row.isActive ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                void (async () => {
                  try {
                    await restoreFairStandAdminPreview(row.id);
                    await load();
                  } catch (restoreError) {
                    setError(
                      restoreError instanceof Error
                        ? restoreError.message
                        : adminLabels.fairStandPreviewsRestoreError,
                    );
                  }
                })();
              }}
            >
              {adminLabels.fairStandPreviewsActionRestore}
            </Button>
          ) : null}
        </TableRowActions>
      ),
    },
  ];

  const liveDefinition = form
    ? { id: editing?.id ?? 2147483646, markup: form.markup, cssCode: form.css_code }
    : null;

  const baseline: PreviewForm = editing
    ? {
        display_name: editing.displayName,
        markup: editing.markup,
        css_code: editing.cssCode,
        sort_index: String(editing.sortIndex),
        is_active: editing.isActive,
      }
    : emptyPreview;

  return (
    <PageShell>
      <PageHeader
        title={adminLabels.fairStandPreviewsTitle}
        subtitle={adminLabels.fairStandPreviewsSubtitle}
        actions={
          canCreate ? (
            <Button
              variant="primary"
              onClick={() => {
                setEditing(null);
                setForm(emptyPreview);
              }}
            >
              {adminLabels.fairStandPreviewsCreate}
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandPreviewsPermissionDenied}</Banner> : null}
      {loading ? <LoadingState /> : null}
      {canRead && !loading && !error ? (
        <section>
          <SectionHeader
            title={adminLabels.fairStandPreviewsTableTitle}
            description={adminLabels.fairStandPreviewsTableDescription}
          />
          <UniversalDataTable
            items={filteredPreviews}
            columns={columns}
            rowKey={(row) => String(row.id)}
            toolbar={
              <FilterPanel
                actions={
                  <Button variant="secondary" onClick={() => void load()}>
                    {adminLabels.fairStandPreviewsRefresh}
                  </Button>
                }
              >
                <FormField
                  label={adminLabels.fairStandPreviewsFilterSearch}
                  htmlFor="fs-previews-search"
                >
                  <TextInput
                    id="fs-previews-search"
                    value={search}
                    placeholder={adminLabels.fairStandPreviewsFilterSearchPlaceholder}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </FormField>
              </FilterPanel>
            }
            emptyState={
              <EmptyState
                title={adminLabels.fairStandPreviewsEmptyTitle}
                description={adminLabels.fairStandPreviewsEmptyDescription}
              />
            }
          />
        </section>
      ) : null}

      {form ? (
        <FormDirtyHost onClose={closeModal}>
          <FormDirtyReporter values={form} baseline={baseline} />
          <FormModal
            title={
              editing
                ? adminLabels.fairStandPreviewsEditTitle
                : adminLabels.fairStandPreviewsCreateTitle
            }
            onClose={closeModal}
            size="lg"
            formWidth="wide"
            footer={
              <>
                <Button variant="secondary" onClick={closeModal}>
                  {adminLabels.fairStandPreviewsCancel}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    void (async () => {
                      try {
                        if (editing) {
                          await updateFairStandAdminPreview(editing.id, {
                            display_name: form.display_name,
                            markup: form.markup,
                            css_code: form.css_code,
                            sort_index: Number(form.sort_index),
                            is_active: form.is_active,
                          });
                        } else {
                          await createFairStandAdminPreview({
                            display_name: form.display_name,
                            markup: form.markup,
                            css_code: form.css_code,
                            sort_index: Number(form.sort_index),
                            is_active: form.is_active,
                          });
                        }
                        closeModal();
                        await load();
                      } catch (saveError) {
                        setError(
                          saveError instanceof Error
                            ? saveError.message
                            : adminLabels.fairStandPreviewsSaveError,
                        );
                      }
                    })();
                  }}
                >
                  {adminLabels.fairStandPreviewsSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandPreviewsSectionIdentity}>
              <FormGrid columns={2}>
                {editing ? (
                  <FormField label={adminLabels.fairStandPreviewsFieldId} htmlFor="preview-id">
                    <TextInput id="preview-id" value={String(editing.id)} disabled readOnly />
                  </FormField>
                ) : null}
                <FormField
                  label={adminLabels.fairStandPreviewsFieldName}
                  htmlFor="preview-name"
                  hint={adminLabels.fairStandPreviewsFieldNameHint}
                  required
                >
                  <TextInput
                    id="preview-name"
                    value={form.display_name}
                    onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                    required
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandPreviewsFieldIndex}
                  htmlFor="preview-index"
                  hint={adminLabels.fairStandPreviewsFieldIndexHint}
                  required
                >
                  <TextInput
                    id="preview-index"
                    type="number"
                    min={1}
                    step={1}
                    value={form.sort_index}
                    onChange={(event) => setForm({ ...form, sort_index: event.target.value })}
                    required
                  />
                </FormField>
              </FormGrid>
              <CheckboxField
                id="preview-active"
                label={adminLabels.fairStandPreviewsFieldActive}
                hint={adminLabels.fairStandPreviewsFieldActiveHint}
                checked={form.is_active}
                onChange={(checked: boolean) => setForm({ ...form, is_active: checked })}
              />
            </FormSection>

            <FormSection title={adminLabels.fairStandPreviewsSectionMarkup}>
              <FormField
                label={adminLabels.fairStandPreviewsFieldMarkup}
                htmlFor="preview-markup"
                hint={adminLabels.fairStandPreviewsFieldMarkupHint}
                fullWidth
              >
                <TextareaInput
                  id="preview-markup"
                  value={form.markup}
                  onChange={(event) => setForm({ ...form, markup: event.target.value })}
                />
              </FormField>
              <FormField
                label={adminLabels.fairStandPreviewsFieldCss}
                htmlFor="preview-css"
                hint={adminLabels.fairStandPreviewsFieldCssHint}
                fullWidth
              >
                <TextareaInput
                  id="preview-css"
                  value={form.css_code}
                  onChange={(event) => setForm({ ...form, css_code: event.target.value })}
                />
              </FormField>
            </FormSection>

            <FormSection title={adminLabels.fairStandPreviewsSectionLivePreview}>
              <FormField
                label={adminLabels.fairStandPreviewsFieldLivePreview}
                htmlFor="preview-live"
                fullWidth
              >
                <FairStandCatalogLivePreview id="preview-live" definition={liveDefinition} />
              </FormField>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title={adminLabels.fairStandPreviewsArchiveTitle}
          message={adminLabels.fairStandPreviewsArchiveMessage.replace("{name}", archiveTarget.displayName)}
          confirmLabel={adminLabels.fairStandPreviewsArchiveConfirm}
          variant="danger"
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminPreview(archiveTarget.id);
                setArchiveTarget(null);
                await load();
              } catch (archiveError) {
                setError(
                  archiveError instanceof Error
                    ? archiveError.message
                    : adminLabels.fairStandPreviewsArchiveError,
                );
                setArchiveTarget(null);
              }
            })();
          }}
        />
      ) : null}
    </PageShell>
  );
}
