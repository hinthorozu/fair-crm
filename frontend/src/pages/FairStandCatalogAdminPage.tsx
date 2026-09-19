import React from "react";
import {
  archiveFairStandAdminCategory,
  createFairStandAdminCategory,
  listFairStandAdminCategories,
  listFairStandAdminItems,
  listFairStandAdminPreviews,
  restoreFairStandAdminCategory,
  updateFairStandAdminCategory,
  updateFairStandAdminItem,
  type FairStandAdminCategory,
  type FairStandAdminItem,
  type FairStandAdminPreview,
} from "../api/fairStandAdmin";
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
  SelectInput,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import {
  FAIR_STAND_CATALOG_ARCHIVE,
  FAIR_STAND_CATALOG_CREATE,
  FAIR_STAND_CATALOG_READ,
  FAIR_STAND_CATALOG_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";
import {
  categorySaveErrorMessage,
  categoryWritePayload,
  nextCatalogIndex,
} from "../utils/fairStandCategoryAdmin";

type CategoryForm = { catalog_name: string; catalog_index: string; is_active: boolean };
type ItemForm = {
  catalog_visible: boolean;
  category_id: string;
  catalog_item_index: string;
  preview_id: string;
};

const emptyCategory: CategoryForm = { catalog_name: "", catalog_index: "1", is_active: true };

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

export function FairStandCatalogAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_CATALOG_READ);
  const canCreate = granted.has(FAIR_STAND_CATALOG_CREATE);
  const canUpdate = granted.has(FAIR_STAND_CATALOG_UPDATE);
  const canArchive = granted.has(FAIR_STAND_CATALOG_ARCHIVE);
  const [categories, setCategories] = React.useState<FairStandAdminCategory[]>([]);
  const [items, setItems] = React.useState<FairStandAdminItem[]>([]);
  const [previews, setPreviews] = React.useState<FairStandAdminPreview[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [categoryForm, setCategoryForm] = React.useState<CategoryForm | null>(null);
  const [categoryEditing, setCategoryEditing] = React.useState<FairStandAdminCategory | null>(null);
  const [categoryFormError, setCategoryFormError] = React.useState<string | null>(null);
  const [itemEditing, setItemEditing] = React.useState<FairStandAdminItem | null>(null);
  const [itemForm, setItemForm] = React.useState<ItemForm | null>(null);
  const [archiveTarget, setArchiveTarget] = React.useState<FairStandAdminCategory | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextCategories, nextItems, nextPreviews] = await Promise.all([
        listFairStandAdminCategories(),
        listFairStandAdminItems(),
        listFairStandAdminPreviews().catch(() => [] as FairStandAdminPreview[]),
      ]);
      setCategories(nextCategories);
      setItems(nextItems);
      setPreviews(nextPreviews.filter((preview) => preview.isActive));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Katalog yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const closeCategoryModal = React.useCallback(() => {
    setCategoryForm(null);
    setCategoryEditing(null);
    setCategoryFormError(null);
  }, []);

  const openCreateCategory = () => {
    setCategoryEditing(null);
    setCategoryFormError(null);
    setCategoryForm({ ...emptyCategory, catalog_index: nextCatalogIndex(categories) });
  };

  const openEditCategory = (row: FairStandAdminCategory) => {
    setCategoryEditing(row);
    setCategoryFormError(null);
    setCategoryForm({
      catalog_name: row.catalogName,
      catalog_index: String(row.catalogIndex),
      is_active: row.isActive,
    });
  };

  const categoryNameById = React.useMemo(
    () => new Map(categories.map((category) => [category.id, category.catalogName])),
    [categories],
  );
  const previewNameById = React.useMemo(
    () => new Map(previews.map((preview) => [preview.id, preview.displayName])),
    [previews],
  );

  const categoryColumns: UniversalDataTableColumn<FairStandAdminCategory>[] = [
    { key: "id", header: "ID", render: (row) => String(row.id) },
    { key: "name", header: "Ad", render: (row) => row.catalogName },
    { key: "index", header: "Sıra", render: (row) => String(row.catalogIndex) },
    { key: "active", header: "Durum", render: (row) => (row.isActive ? "Aktif" : "Pasif") },
    {
      key: "actions",
      header: "İşlemler",
      render: (row) => (
        <div className="table-row-actions">
          {canUpdate ? (
            <Button size="sm" onClick={() => openEditCategory(row)}>
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
                    await restoreFairStandAdminCategory(row.id);
                    await load();
                  } catch (restoreError) {
                    setError(restoreError instanceof Error ? restoreError.message : "Kategori aktifleştirilemedi.");
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

  const itemColumns: UniversalDataTableColumn<FairStandAdminItem>[] = [
    { key: "item", header: "Item", render: (row) => `${row.name} (${row.itemKey})` },
    { key: "visible", header: "Katalogda", render: (row) => (row.catalogVisible ? "Evet" : "Hayır") },
    {
      key: "category",
      header: "Kategori",
      render: (row) => (row.categoryId == null ? "—" : (categoryNameById.get(row.categoryId) ?? String(row.categoryId))),
    },
    { key: "index", header: "Sıra", render: (row) => String(row.catalogItemIndex ?? "—") },
    { key: "preview", header: "Önizleme", render: (row) => previewNameById.get(row.previewId ?? -1) ?? (row.previewId == null ? "—" : String(row.previewId)) },
    {
      key: "actions",
      header: "İşlemler",
      render: (row) =>
        canUpdate ? (
          <Button
            size="sm"
            onClick={() => {
              setItemEditing(row);
              setItemForm({
                catalog_visible: row.catalogVisible,
                category_id: row.categoryId == null ? "" : String(row.categoryId),
                catalog_item_index: String(row.catalogItemIndex ?? ""),
                preview_id: row.previewId == null ? "" : String(row.previewId),
              });
            }}
          >
            Katalog bağını düzenle
          </Button>
        ) : null,
    },
  ];

  return (
    <PageShell>
      <PageHeader
        title="Katalog Yönetimi"
        subtitle="Fair Stand kategori ve Item katalog bağlarını yönetin"
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreateCategory}>
              Kategori ekle
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!canRead ? <Banner variant="info">Bu ekranı görmek için Super Admin katalog okuma yetkisi gerekir.</Banner> : null}
      {loading ? <LoadingState /> : null}
      {canRead && !loading && !error ? (
        <>
          <section>
            <PageHeader title="Kategoriler" />
            <UniversalDataTable
              items={categories}
              columns={categoryColumns}
              rowKey={(row) => String(row.id)}
              emptyState={<EmptyState title="Kategori yok" description="İlk kategoriyi oluşturun." />}
            />
          </section>
          <section>
            <PageHeader title="Item katalog bağları" />
            <UniversalDataTable
              items={items}
              columns={itemColumns}
              rowKey={(row) => row.itemKey}
              emptyState={<EmptyState title="Item yok" description="Katalog Item kaydı bulunamadı." />}
            />
          </section>
        </>
      ) : null}

      {categoryForm ? (
        <FormDirtyHost onClose={closeCategoryModal}>
          <FormDirtyReporter
            values={categoryForm}
            baseline={
              categoryEditing
                ? {
                    catalog_name: categoryEditing.catalogName,
                    catalog_index: String(categoryEditing.catalogIndex),
                    is_active: categoryEditing.isActive,
                  }
                : emptyCategory
            }
          />
          <FormModal
            title={categoryEditing ? "Kategori düzenle" : "Kategori oluştur"}
            onClose={closeCategoryModal}
            footer={
              <>
                <Button variant="secondary" onClick={closeCategoryModal}>
                  Vazgeç
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    void (async () => {
                      const payload = categoryWritePayload(categoryForm);
                      const indexCollision = categories.some(
                        (category) =>
                          category.catalogIndex === payload.catalog_index &&
                          category.id !== categoryEditing?.id,
                      );
                      if (indexCollision) {
                        setCategoryFormError("Bu sıra numarası zaten kullanılıyor.");
                        return;
                      }
                      try {
                        if (categoryEditing) {
                          await updateFairStandAdminCategory(categoryEditing.id, payload);
                        } else {
                          await createFairStandAdminCategory(payload);
                        }
                        closeCategoryModal();
                        await load();
                      } catch (saveError) {
                        setCategoryFormError(
                          categorySaveErrorMessage(
                            saveError instanceof Error ? saveError.message : "Kategori kaydedilemedi.",
                          ),
                        );
                      }
                    })();
                  }}
                >
                  Kaydet
                </Button>
              </>
            }
          >
            {categoryFormError ? <Banner variant="error">{categoryFormError}</Banner> : null}
            {categoryEditing ? (
              <FormField label="ID" htmlFor="catalog-id">
                <TextInput id="catalog-id" value={String(categoryEditing.id)} disabled />
              </FormField>
            ) : null}
            <FormField label="Ad" htmlFor="catalog-name">
              <TextInput
                id="catalog-name"
                value={categoryForm.catalog_name}
                onChange={(event) => setCategoryForm({ ...categoryForm, catalog_name: event.target.value })}
              />
            </FormField>
            <FormField label="Sıra" htmlFor="catalog-index">
              <TextInput
                id="catalog-index"
                value={categoryForm.catalog_index}
                onChange={(event) => setCategoryForm({ ...categoryForm, catalog_index: event.target.value })}
              />
            </FormField>
            <CheckboxField
              id="catalog-active"
              label="Aktif"
              checked={categoryForm.is_active}
              onChange={(event) => setCategoryForm({ ...categoryForm, is_active: event.target.checked })}
            />
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {itemForm && itemEditing ? (
        <FormDirtyHost onClose={() => setItemForm(null)}>
          <FormDirtyReporter
            values={itemForm}
            baseline={{
              catalog_visible: itemEditing.catalogVisible,
              category_id: itemEditing.categoryId == null ? "" : String(itemEditing.categoryId),
              catalog_item_index: String(itemEditing.catalogItemIndex ?? ""),
              preview_id: itemEditing.previewId == null ? "" : String(itemEditing.previewId),
            }}
          />
          <FormModal
            title={`${itemEditing.name} katalog bağı`}
            onClose={() => setItemForm(null)}
            footer={
              <>
                <Button variant="secondary" onClick={() => setItemForm(null)}>
                  Vazgeç
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    void (async () => {
                      try {
                        await updateFairStandAdminItem(itemEditing.itemKey, {
                          catalog_visible: itemForm.catalog_visible,
                          category_id: itemForm.category_id ? Number(itemForm.category_id) : null,
                          catalog_item_index: itemForm.catalog_item_index ? Number(itemForm.catalog_item_index) : null,
                          preview_id: itemForm.preview_id ? Number(itemForm.preview_id) : null,
                        });
                        setItemForm(null);
                        setItemEditing(null);
                        await load();
                      } catch (saveError) {
                        setError(saveError instanceof Error ? saveError.message : "Item katalog bağı kaydedilemedi.");
                      }
                    })();
                  }}
                >
                  Kaydet
                </Button>
              </>
            }
          >
            <CheckboxField
              id="item-visible"
              label="Katalogda görünsün"
              checked={itemForm.catalog_visible}
              onChange={(event) => setItemForm({ ...itemForm, catalog_visible: event.target.checked })}
            />
            <FormField label="Kategori" htmlFor="item-category">
              <SelectInput
                id="item-category"
                value={itemForm.category_id}
                onChange={(event) => setItemForm({ ...itemForm, category_id: event.target.value })}
              >
                <option value="">Seçin</option>
                {categories.filter((category) => category.isActive).map((category) => (
                  <option key={category.id} value={String(category.id)}>
                    {category.catalogName}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Katalog sırası" htmlFor="item-index">
              <TextInput
                id="item-index"
                value={itemForm.catalog_item_index}
                onChange={(event) => setItemForm({ ...itemForm, catalog_item_index: event.target.value })}
              />
            </FormField>
            <FormField label="Katalog önizlemesi" htmlFor="item-preview">
              <SelectInput
                id="item-preview"
                value={itemForm.preview_id}
                onChange={(event) => setItemForm({ ...itemForm, preview_id: event.target.value })}
              >
                <option value="">Seçin</option>
                {previews.filter((preview) => preview.isActive || preview.id === itemEditing.previewId).map((preview) => (
                  <option key={preview.id} value={String(preview.id)}>
                    {preview.displayName}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title="Kategoriyi pasifleştir"
          message={`${archiveTarget.catalogName} kategorisi fiziksel silinmez; pasifleştirilir.`}
          confirmLabel="Pasifleştir"
          variant="danger"
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminCategory(archiveTarget.id);
                setArchiveTarget(null);
                await load();
              } catch (archiveError) {
                setError(archiveError instanceof Error ? archiveError.message : "Kategori pasifleştirilemedi.");
                setArchiveTarget(null);
              }
            })();
          }}
        />
      ) : null}
    </PageShell>
  );
}
