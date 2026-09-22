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
import { FairStandCatalogPreviewSelect } from "../components/FairStandCatalogPreviewSelect";
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
  SelectInput,
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

function matchesCategorySearch(row: FairStandAdminCategory, search: string): boolean {
  const q = search.trim().toLocaleLowerCase("tr-TR");
  if (!q) return true;
  return (
    row.catalogName.toLocaleLowerCase("tr-TR").includes(q) ||
    String(row.id).includes(q) ||
    String(row.catalogIndex).includes(q)
  );
}

function matchesItemSearch(
  row: FairStandAdminItem,
  search: string,
  categoryName: string | undefined,
  previewName: string | undefined,
): boolean {
  const q = search.trim().toLocaleLowerCase("tr-TR");
  if (!q) return true;
  return (
    row.name.toLocaleLowerCase("tr-TR").includes(q) ||
    row.itemKey.toLocaleLowerCase("tr-TR").includes(q) ||
    (categoryName ?? "").toLocaleLowerCase("tr-TR").includes(q) ||
    (previewName ?? "").toLocaleLowerCase("tr-TR").includes(q) ||
    (row.categoryId != null && String(row.categoryId).includes(q)) ||
    (row.previewId != null && String(row.previewId).includes(q))
  );
}

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
  const [categorySearch, setCategorySearch] = React.useState("");
  const [itemSearch, setItemSearch] = React.useState("");
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
      setPreviews(nextPreviews);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandCatalogLoadError);
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

  const closeItemModal = React.useCallback(() => {
    setItemForm(null);
    setItemEditing(null);
  }, []);

  const openEditItem = (row: FairStandAdminItem) => {
    setItemEditing(row);
    setItemForm({
      catalog_visible: row.catalogVisible,
      category_id: row.categoryId == null ? "" : String(row.categoryId),
      catalog_item_index: String(row.catalogItemIndex ?? ""),
      preview_id: row.previewId == null ? "" : String(row.previewId),
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

  const filteredCategories = React.useMemo(
    () => categories.filter((row) => matchesCategorySearch(row, categorySearch)),
    [categories, categorySearch],
  );
  const filteredItems = React.useMemo(
    () =>
      items.filter((row) =>
        matchesItemSearch(
          row,
          itemSearch,
          row.categoryId == null ? undefined : categoryNameById.get(row.categoryId),
          row.previewId == null ? undefined : previewNameById.get(row.previewId),
        ),
      ),
    [items, itemSearch, categoryNameById, previewNameById],
  );

  const categoryColumns: UniversalDataTableColumn<FairStandAdminCategory>[] = [
    { key: "id", title: adminLabels.fairStandCatalogColId, sortable: false, render: (row) => String(row.id) },
    { key: "name", title: adminLabels.fairStandCatalogColName, sortable: false, render: (row) => row.catalogName },
    {
      key: "index",
      title: adminLabels.fairStandCatalogColIndex,
      sortable: false,
      render: (row) => String(row.catalogIndex),
    },
    {
      key: "active",
      title: adminLabels.fairStandCatalogColStatus,
      sortable: false,
      render: (row) => (
        <Badge variant={row.isActive ? "success" : "neutral"}>
          {row.isActive
            ? adminLabels.fairStandCatalogStatusActive
            : adminLabels.fairStandCatalogStatusInactive}
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
            <Button size="sm" variant="secondary" onClick={() => openEditCategory(row)}>
              {adminLabels.fairStandCatalogActionEdit}
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
                    await restoreFairStandAdminCategory(row.id);
                    await load();
                  } catch (restoreError) {
                    setError(
                      restoreError instanceof Error
                        ? restoreError.message
                        : adminLabels.fairStandCatalogRestoreError,
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

  const itemColumns: UniversalDataTableColumn<FairStandAdminItem>[] = [
    {
      key: "item",
      title: adminLabels.fairStandCatalogColItem,
      sortable: false,
      render: (row) => `${row.name} (${row.itemKey})`,
    },
    {
      key: "visible",
      title: adminLabels.fairStandCatalogColVisible,
      sortable: false,
      render: (row) => (
        <Badge variant={row.catalogVisible ? "success" : "neutral"}>
          {row.catalogVisible
            ? adminLabels.fairStandCatalogVisibleYes
            : adminLabels.fairStandCatalogVisibleNo}
        </Badge>
      ),
    },
    {
      key: "category",
      title: adminLabels.fairStandCatalogColCategory,
      sortable: false,
      render: (row) =>
        row.categoryId == null
          ? adminLabels.fairStandCatalogNone
          : (categoryNameById.get(row.categoryId) ?? String(row.categoryId)),
    },
    {
      key: "index",
      title: adminLabels.fairStandCatalogColIndex,
      sortable: false,
      render: (row) => String(row.catalogItemIndex ?? adminLabels.fairStandCatalogNone),
    },
    {
      key: "preview",
      title: adminLabels.fairStandCatalogColPreview,
      sortable: false,
      render: (row) =>
        previewNameById.get(row.previewId ?? -1) ??
        (row.previewId == null ? adminLabels.fairStandCatalogNone : String(row.previewId)),
    },
    {
      key: "actions",
      title: adminLabels.fairStandCatalogColActions,
      sortable: false,
      render: (row) =>
        canUpdate ? (
          <TableRowActions>
            <Button size="sm" variant="secondary" onClick={() => openEditItem(row)}>
              {adminLabels.fairStandCatalogActionEditItem}
            </Button>
          </TableRowActions>
        ) : null,
    },
  ];

  const categoryBaseline: CategoryForm = categoryEditing
    ? {
        catalog_name: categoryEditing.catalogName,
        catalog_index: String(categoryEditing.catalogIndex),
        is_active: categoryEditing.isActive,
      }
    : emptyCategory;

  const itemBaseline: ItemForm | null = itemEditing
    ? {
        catalog_visible: itemEditing.catalogVisible,
        category_id: itemEditing.categoryId == null ? "" : String(itemEditing.categoryId),
        catalog_item_index: String(itemEditing.catalogItemIndex ?? ""),
        preview_id: itemEditing.previewId == null ? "" : String(itemEditing.previewId),
      }
    : null;

  return (
    <PageShell>
      <PageHeader
        title={adminLabels.fairStandCatalogTitle}
        subtitle={adminLabels.fairStandCatalogSubtitle}
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreateCategory}>
              {adminLabels.fairStandCatalogCategoryCreate}
            </Button>
          ) : null
        }
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandCatalogPermissionDenied}</Banner> : null}
      {loading ? <LoadingState /> : null}
      {canRead && !loading && !error ? (
        <>
          <section>
            <SectionHeader
              title={adminLabels.fairStandCatalogCategorySection}
              description={adminLabels.fairStandCatalogCategoryDescription}
            />
            <UniversalDataTable
              items={filteredCategories}
              columns={categoryColumns}
              rowKey={(row) => String(row.id)}
              toolbar={
                <FilterPanel
                  actions={
                    <Button variant="secondary" onClick={() => void load()}>
                      {adminLabels.fairStandCatalogRefresh}
                    </Button>
                  }
                >
                  <FormField
                    label={adminLabels.fairStandCatalogCategoryFilterSearch}
                    htmlFor="fs-catalog-category-search"
                  >
                    <TextInput
                      id="fs-catalog-category-search"
                      value={categorySearch}
                      placeholder={adminLabels.fairStandCatalogCategoryFilterSearchPlaceholder}
                      onChange={(event) => setCategorySearch(event.target.value)}
                    />
                  </FormField>
                </FilterPanel>
              }
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandCatalogCategoryEmptyTitle}
                  description={adminLabels.fairStandCatalogCategoryEmptyDescription}
                />
              }
            />
          </section>
          <section>
            <SectionHeader
              title={adminLabels.fairStandCatalogItemSection}
              description={adminLabels.fairStandCatalogItemDescription}
            />
            <UniversalDataTable
              items={filteredItems}
              columns={itemColumns}
              rowKey={(row) => row.itemKey}
              toolbar={
                <FilterPanel>
                  <FormField
                    label={adminLabels.fairStandCatalogItemFilterSearch}
                    htmlFor="fs-catalog-item-search"
                  >
                    <TextInput
                      id="fs-catalog-item-search"
                      value={itemSearch}
                      placeholder={adminLabels.fairStandCatalogItemFilterSearchPlaceholder}
                      onChange={(event) => setItemSearch(event.target.value)}
                    />
                  </FormField>
                </FilterPanel>
              }
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandCatalogItemEmptyTitle}
                  description={adminLabels.fairStandCatalogItemEmptyDescription}
                />
              }
            />
          </section>
        </>
      ) : null}

      {categoryForm ? (
        <FormDirtyHost onClose={closeCategoryModal}>
          <FormDirtyReporter values={categoryForm} baseline={categoryBaseline} />
          <FormModal
            title={
              categoryEditing
                ? adminLabels.fairStandCatalogCategoryEditTitle
                : adminLabels.fairStandCatalogCategoryCreateTitle
            }
            onClose={closeCategoryModal}
            formWidth="narrow"
            footer={
              <>
                <Button variant="secondary" onClick={closeCategoryModal}>
                  {adminLabels.fairStandCatalogCancel}
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
                        setCategoryFormError(adminLabels.fairStandCatalogIndexCollision);
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
                            saveError instanceof Error
                              ? saveError.message
                              : adminLabels.fairStandCatalogCategorySaveError,
                          ),
                        );
                      }
                    })();
                  }}
                >
                  {adminLabels.fairStandCatalogSave}
                </Button>
              </>
            }
          >
            {categoryFormError ? <Banner variant="error">{categoryFormError}</Banner> : null}
            <FormSection title={adminLabels.fairStandCatalogCategoryModalSection}>
              <FormGrid columns={2}>
                {categoryEditing ? (
                  <FormField label={adminLabels.fairStandCatalogFieldId} htmlFor="catalog-id">
                    <TextInput id="catalog-id" value={String(categoryEditing.id)} disabled readOnly />
                  </FormField>
                ) : null}
                <FormField
                  label={adminLabels.fairStandCatalogFieldName}
                  htmlFor="catalog-name"
                  hint={adminLabels.fairStandCatalogFieldNameHint}
                  required
                >
                  <TextInput
                    id="catalog-name"
                    value={categoryForm.catalog_name}
                    onChange={(event) =>
                      setCategoryForm({ ...categoryForm, catalog_name: event.target.value })
                    }
                    required
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandCatalogFieldIndex}
                  htmlFor="catalog-index"
                  hint={adminLabels.fairStandCatalogFieldIndexHint}
                  required
                >
                  <TextInput
                    id="catalog-index"
                    type="number"
                    min={1}
                    step={1}
                    value={categoryForm.catalog_index}
                    onChange={(event) =>
                      setCategoryForm({ ...categoryForm, catalog_index: event.target.value })
                    }
                    required
                  />
                </FormField>
              </FormGrid>
              <CheckboxField
                id="catalog-active"
                label={adminLabels.fairStandCatalogFieldActive}
                hint={adminLabels.fairStandCatalogFieldActiveHint}
                checked={categoryForm.is_active}
                onChange={(checked: boolean) =>
                  setCategoryForm({ ...categoryForm, is_active: checked })
                }
              />
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {itemForm && itemEditing && itemBaseline ? (
        <FormDirtyHost onClose={closeItemModal}>
          <FormDirtyReporter values={itemForm} baseline={itemBaseline} />
          <FormModal
            title={adminLabels.fairStandCatalogItemModalTitle.replace("{name}", itemEditing.name)}
            onClose={closeItemModal}
            formWidth="standard"
            footer={
              <>
                <Button variant="secondary" onClick={closeItemModal}>
                  {adminLabels.fairStandCatalogCancel}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    void (async () => {
                      try {
                        await updateFairStandAdminItem(itemEditing.itemKey, {
                          catalog_visible: itemForm.catalog_visible,
                          category_id: itemForm.category_id ? Number(itemForm.category_id) : null,
                          catalog_item_index: itemForm.catalog_item_index
                            ? Number(itemForm.catalog_item_index)
                            : null,
                          preview_id: itemForm.preview_id ? Number(itemForm.preview_id) : null,
                        });
                        closeItemModal();
                        await load();
                      } catch (saveError) {
                        setError(
                          saveError instanceof Error
                            ? saveError.message
                            : adminLabels.fairStandCatalogItemSaveError,
                        );
                      }
                    })();
                  }}
                >
                  {adminLabels.fairStandCatalogSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandCatalogItemModalSection}>
              <CheckboxField
                id="item-visible"
                label={adminLabels.fairStandCatalogFieldItemVisible}
                hint={adminLabels.fairStandCatalogFieldItemVisibleHint}
                checked={itemForm.catalog_visible}
                onChange={(checked: boolean) =>
                  setItemForm({ ...itemForm, catalog_visible: checked })
                }
              />
              <FormGrid columns={2}>
                <FormField
                  label={adminLabels.fairStandCatalogFieldItemCategory}
                  htmlFor="item-category"
                  hint={adminLabels.fairStandCatalogFieldItemCategoryHint}
                >
                  <SelectInput
                    id="item-category"
                    value={itemForm.category_id}
                    onChange={(event) => setItemForm({ ...itemForm, category_id: event.target.value })}
                  >
                    <option value="">{adminLabels.fairStandCatalogSelectPlaceholder}</option>
                    {categories
                      .filter((category) => category.isActive)
                      .map((category) => (
                        <option key={category.id} value={String(category.id)}>
                          {category.catalogName}
                        </option>
                      ))}
                  </SelectInput>
                </FormField>
                <FormField
                  label={adminLabels.fairStandCatalogFieldItemIndex}
                  htmlFor="item-index"
                  hint={adminLabels.fairStandCatalogFieldItemIndexHint}
                >
                  <TextInput
                    id="item-index"
                    type="number"
                    min={1}
                    step={1}
                    value={itemForm.catalog_item_index}
                    onChange={(event) =>
                      setItemForm({ ...itemForm, catalog_item_index: event.target.value })
                    }
                  />
                </FormField>
              </FormGrid>
              <FormField
                label={adminLabels.fairStandCatalogFieldItemPreview}
                htmlFor="item-preview"
                hint={adminLabels.fairStandCatalogFieldItemPreviewHint}
                fullWidth
              >
                <FairStandCatalogPreviewSelect
                  id="item-preview"
                  value={itemForm.preview_id}
                  previews={previews}
                  onChange={(previewId) => setItemForm({ ...itemForm, preview_id: previewId })}
                />
              </FormField>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {archiveTarget ? (
        <ConfirmDialog
          title={adminLabels.fairStandCatalogArchiveTitle}
          message={adminLabels.fairStandCatalogArchiveMessage.replace("{name}", archiveTarget.catalogName)}
          confirmLabel={adminLabels.fairStandCatalogArchiveConfirm}
          variant="danger"
          onCancel={() => setArchiveTarget(null)}
          onConfirm={() => {
            void (async () => {
              try {
                await archiveFairStandAdminCategory(archiveTarget.id);
                setArchiveTarget(null);
                await load();
              } catch (archiveError) {
                setError(
                  archiveError instanceof Error
                    ? archiveError.message
                    : adminLabels.fairStandCatalogArchiveError,
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
