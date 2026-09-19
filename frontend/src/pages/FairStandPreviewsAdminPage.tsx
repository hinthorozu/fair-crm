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
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import {
  CheckboxField,
  FormDirtyHost,
  FormField,
  FormModal,
  TextareaInput,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
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
  const [form, setForm] = React.useState<PreviewForm | null>(null);
  const [editing, setEditing] = React.useState<FairStandAdminPreview | null>(null);
  const [archiveTarget, setArchiveTarget] = React.useState<FairStandAdminPreview | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPreviews(await listFairStandAdminPreviews());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Önizlemeler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const columns: UniversalDataTableColumn<FairStandAdminPreview>[] = [
    { key: "id", header: "ID", render: (row) => String(row.id) },
    { key: "name", header: "Ad", render: (row) => row.displayName },
    { key: "index", header: "Sıra", render: (row) => String(row.sortIndex) },
    { key: "active", header: "Durum", render: (row) => (row.isActive ? "Aktif" : "Pasif") },
    {
      key: "live",
      header: "Canlı önizleme",
      render: (row) => <FairStandCatalogLivePreview definition={row} />,
    },
    {
      key: "actions",
      header: "İşlemler",
      render: (row) => (
        <div className="table-row-actions">
          {canUpdate ? (
            <Button
              size="sm"
              onClick={() => {
                setEditing(row);
                setForm({
                  display_name: row.displayName,
                  markup: row.markup,
                  css_code: row.cssCode,
                  sort_index: String(row.sortIndex),
                  is_active: row.isActive,
                });
              }}
            >
              Düzenle
            </Button>
          ) : null}
          {canArchive && row.isActive ? (
            <Button size="sm" variant="danger" onClick={() => setArchiveTarget(row)}>
              Pasifleştir
            </Button>
          ) : null}
          {canArchive && !row.isActive ? (
            <Button
              size="sm"
              onClick={() => {
                void (async () => {
                  try {
                    await restoreFairStandAdminPreview(row.id);
                    await load();
                  } catch (restoreError) {
                    setError(restoreError instanceof Error ? restoreError.message : "Önizleme aktifleştirilemedi.");
                  }
                })();
              }}
            >
              Aktifleştir
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  const liveDefinition = form
    ? { id: editing?.id ?? 2147483646, markup: form.markup, cssCode: form.css_code }
    : null;

  return (
    <PageShell>
      <PageHeader
        title="Katalog Önizlemeleri"
        subtitle="Fair Stand katalog silüet tanımlarını yönetin"
        actions={
          canCreate ? (
            <Button
              variant="primary"
              onClick={() => {
                setEditing(null);
                setForm(emptyPreview);
              }}
            >
              Önizleme ekle
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!canRead ? (
        <Banner variant="info">Bu ekranı görmek için Super Admin önizleme okuma yetkisi gerekir.</Banner>
      ) : null}
      {loading ? <LoadingState /> : null}
      {canRead && !loading && !error ? (
        <UniversalDataTable
          items={previews}
          columns={columns}
          rowKey={(row) => String(row.id)}
          emptyState={<EmptyState title="Önizleme yok" description="İlk katalog önizlemesini oluşturun." />}
        />
      ) : null}

      {form ? (
        <FormDirtyHost onClose={() => setForm(null)}>
          <FormDirtyReporter
            values={form}
            baseline={
              editing
                ? {
                    display_name: editing.displayName,
                    markup: editing.markup,
                    css_code: editing.cssCode,
                    sort_index: String(editing.sortIndex),
                    is_active: editing.isActive,
                  }
                : emptyPreview
            }
          />
          <FormModal
            title={editing ? "Önizleme düzenle" : "Önizleme oluştur"}
            onClose={() => setForm(null)}
            size="lg"
            footer={
              <>
                <Button variant="secondary" onClick={() => setForm(null)}>
                  Vazgeç
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
                        setForm(null);
                        setEditing(null);
                        await load();
                      } catch (saveError) {
                        setError(saveError instanceof Error ? saveError.message : "Önizleme kaydedilemedi.");
                      }
                    })();
                  }}
                >
                  Kaydet
                </Button>
              </>
            }
          >
            {editing ? (
              <FormField label="ID" htmlFor="preview-id">
                <TextInput id="preview-id" value={String(editing.id)} readOnly />
              </FormField>
            ) : null}
            <FormField label="Görünen ad" htmlFor="preview-name">
              <TextInput
                id="preview-name"
                value={form.display_name}
                onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              />
            </FormField>
            <FormField label="Sıra" htmlFor="preview-index">
              <TextInput
                id="preview-index"
                value={form.sort_index}
                onChange={(event) => setForm({ ...form, sort_index: event.target.value })}
              />
            </FormField>
            <CheckboxField
              id="preview-active"
              label="Aktif"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            <FormField label="Markup" htmlFor="preview-markup">
              <TextareaInput
                id="preview-markup"
                value={form.markup}
                onChange={(event) => setForm({ ...form, markup: event.target.value })}
              />
            </FormField>
            <FormField label="CSS" htmlFor="preview-css">
              <TextareaInput
                id="preview-css"
                value={form.css_code}
                onChange={(event) => setForm({ ...form, css_code: event.target.value })}
              />
            </FormField>
            <FormField label="Canlı önizleme" htmlFor="preview-live">
              <FairStandCatalogLivePreview definition={liveDefinition} />
            </FormField>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title="Önizlemeyi pasifleştir"
          message={`${archiveTarget.displayName} fiziksel silinmez. Item tarafından kullanılıyorsa işlem reddedilir.`}
          confirmLabel="Pasifleştir"
          variant="danger"
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminPreview(archiveTarget.id);
                setArchiveTarget(null);
                await load();
              } catch (archiveError) {
                setError(archiveError instanceof Error ? archiveError.message : "Önizleme pasifleştirilemedi.");
                setArchiveTarget(null);
              }
            })();
          }}
        />
      ) : null}
    </PageShell>
  );
}
