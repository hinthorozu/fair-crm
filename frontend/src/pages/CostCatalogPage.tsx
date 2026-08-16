import React from "react";
import { createCostCategory, createCostProduct, deleteCostCategory, deleteCostProduct, listCostCategories, listCostProductCategoryOptions, listCostProducts, updateCostCategory, updateCostProduct } from "../api/costCatalog";
import { Banner } from "../components/ui/Banner";
import { EmptyState } from "../components/ui/EmptyState";
import { FormField, FormModal, TextareaInput, TextInput } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { COST_CATEGORY_CREATE, COST_CATEGORY_DELETE, COST_CATEGORY_UPDATE, COST_CATEGORY_VIEW, COST_PRODUCT_CREATE, COST_PRODUCT_DELETE, COST_PRODUCT_UPDATE, COST_PRODUCT_VIEW, getGrantedCostCatalogPermissions } from "../permissions/costCatalogPermissions";
import type { CostCategory, CostCategoryOption, CostCategoryPayload, CostCurrency, CostProduct, CostProductPayload, CostUnit } from "../types/costCatalog";

const emptyCategory: CostCategoryPayload = { name: "", slug: "", description: null };
const emptyProduct: CostProductPayload = { category_id: "", name: "", slug: "", unit: "Adet", unit_price: "0", currency: "TL" };
const units: CostUnit[] = ["Adet", "Kg", "m²", "Metre", "Gün", "Saat"];
const currencies: CostCurrency[] = ["TL", "USD"];

function toSlug(value: string): string {
  return value
    .replace(/[ıİ]/g, "i")
    .replace(/[şŞ]/g, "s")
    .replace(/[ğĞ]/g, "g")
    .replace(/[üÜ]/g, "u")
    .replace(/[öÖ]/g, "o")
    .replace(/[çÇ]/g, "c")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 255)
    .replace(/-+$/g, "");
}

export function CostCatalogPage() {
  const permissions = React.useMemo(() => getGrantedCostCatalogPermissions(), []);
  const canCategoryView = permissions.has(COST_CATEGORY_VIEW);
  const canCategoryCreate = permissions.has(COST_CATEGORY_CREATE);
  const canCategoryUpdate = permissions.has(COST_CATEGORY_UPDATE);
  const canCategoryDelete = permissions.has(COST_CATEGORY_DELETE);
  const canProductView = permissions.has(COST_PRODUCT_VIEW);
  const canProductCreate = permissions.has(COST_PRODUCT_CREATE);
  const canProductUpdate = permissions.has(COST_PRODUCT_UPDATE);
  const canProductDelete = permissions.has(COST_PRODUCT_DELETE);
  const [categories, setCategories] = React.useState<CostCategory[]>([]);
  const [products, setProducts] = React.useState<CostProduct[]>([]);
  const [categoryOptions, setCategoryOptions] = React.useState<CostCategoryOption[]>([]);
  const [categoryEditing, setCategoryEditing] = React.useState<CostCategory | null | undefined>(undefined);
  const [productEditing, setProductEditing] = React.useState<CostProduct | null | undefined>(undefined);
  const [categoryValues, setCategoryValues] = React.useState<CostCategoryPayload>(emptyCategory);
  const [productValues, setProductValues] = React.useState<CostProductPayload>(emptyProduct);
  const [categorySlugTouched, setCategorySlugTouched] = React.useState(false);
  const [productSlugTouched, setProductSlugTouched] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [categoryResult, productResult, optionResult] = await Promise.all([
        canCategoryView ? listCostCategories() : Promise.resolve({ items: [] }),
        canProductView ? listCostProducts() : Promise.resolve({ items: [] }),
        canProductView ? listCostProductCategoryOptions() : Promise.resolve({ items: [] }),
      ]);
      setCategories(categoryResult.items); setProducts(productResult.items); setCategoryOptions(optionResult.items);
    } catch { setError("Maliyet kataloğu yüklenemedi."); }
    finally { setLoading(false); }
  }, [canCategoryView, canProductView]);
  React.useEffect(() => { void load(); }, [load]);

  const saveCategory = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true); setError(null);
    try { categoryEditing ? await updateCostCategory(categoryEditing.id, categoryValues) : await createCostCategory(categoryValues); setCategoryEditing(undefined); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Kategori kaydedilemedi."); }
    finally { setSaving(false); }
  };
  const saveProduct = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true); setError(null);
    try { productEditing ? await updateCostProduct(productEditing.id, productValues) : await createCostProduct(productValues); setProductEditing(undefined); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Ürün kaydedilemedi."); }
    finally { setSaving(false); }
  };
  const removeCategory = async (item: CostCategory) => {
    if (!window.confirm(`“${item.name}” kategorisi silinsin mi?`)) return;
    try { await deleteCostCategory(item.id); await load(); } catch (err) { setError(err instanceof Error ? err.message : "Kategori silinemedi."); }
  };
  const removeProduct = async (item: CostProduct) => {
    if (!window.confirm(`“${item.name}” ürünü silinsin mi?`)) return;
    try { await deleteCostProduct(item.id); await load(); } catch (err) { setError(err instanceof Error ? err.message : "Ürün silinemedi."); }
  };

  const categoryColumns: UniversalDataTableColumn<CostCategory>[] = [
    { key: "name", title: "Kategori", sortable: true, render: (item) => item.name },
    { key: "slug", title: "Slug", sortable: true, render: (item) => item.slug },
    { key: "description", title: "Açıklama", render: (item) => item.description || "—" },
    { key: "actions", title: "İşlemler", render: (item) => <div className="table-actions">{canCategoryUpdate ? <button className="btn secondary" type="button" onClick={() => { setCategoryValues({ name: item.name, slug: item.slug, description: item.description }); setCategorySlugTouched(true); setCategoryEditing(item); }}>Düzenle</button> : null}{canCategoryDelete ? <button className="btn danger" type="button" onClick={() => void removeCategory(item)}>Sil</button> : null}</div> },
  ];
  const productColumns: UniversalDataTableColumn<CostProduct>[] = [
    { key: "name", title: "Ürün", sortable: true, render: (item) => item.name },
    { key: "category", title: "Kategori", sortable: true, render: (item) => item.category_name },
    { key: "unit", title: "Birim", render: (item) => item.unit },
    { key: "price", title: "Birim Fiyat", sortable: true, render: (item) => `${Number(item.unit_price).toLocaleString("tr-TR", { maximumFractionDigits: 4 })} ${item.currency}` },
    { key: "tl", title: "TL Karşılığı", render: (item) => item.currency === "TL" ? `${Number(item.unit_price).toLocaleString("tr-TR", { maximumFractionDigits: 4 })} TL` : "Kur bekleniyor" },
    { key: "actions", title: "İşlemler", render: (item) => <div className="table-actions">{canProductUpdate ? <button className="btn secondary" type="button" onClick={() => { setProductValues({ category_id: item.category_id, name: item.name, slug: item.slug, unit: item.unit, unit_price: item.unit_price, currency: item.currency }); setProductSlugTouched(true); setProductEditing(item); }}>Düzenle</button> : null}{canProductDelete ? <button className="btn danger" type="button" onClick={() => void removeProduct(item)}>Sil</button> : null}</div> },
  ];

  return <PageShell className="cost-catalog-page">
    <PageHeader title="Maliyet Kataloğu" subtitle="Organizasyonunuza ait maliyet kategorilerini ve ürünlerini yönetin" />
    {error ? <Banner variant="error">{error}</Banner> : null}
    {products.some((item) => item.currency === "USD") ? <Banner variant="info">USD/TL kur sağlayıcısı karar kaydında henüz belirlenmediği için USD ürünlerin TL karşılığı bu sürümde hesaplanmıyor.</Banner> : null}
    {canCategoryView ? <section><PageHeader title="Kategoriler" actions={canCategoryCreate ? <button type="button" className="btn primary" onClick={() => { setCategoryValues(emptyCategory); setCategorySlugTouched(false); setCategoryEditing(null); }}>+ Kategori Ekle</button> : null} /><UniversalDataTable items={categories} columns={categoryColumns} rowKey={(item) => item.id} loading={loading} onRetry={() => void load()} emptyState={<EmptyState title="Henüz kategori yok" description="İlk maliyet kategorisini oluşturun." />} /></section> : null}
    {canProductView ? <section><PageHeader title="Ürünler" actions={canProductCreate ? <button type="button" className="btn primary" disabled={!categoryOptions.length} onClick={() => { setProductValues({ ...emptyProduct, category_id: categoryOptions[0]?.id ?? "" }); setProductSlugTouched(false); setProductEditing(null); }}>+ Ürün Ekle</button> : null} /><UniversalDataTable items={products} columns={productColumns} rowKey={(item) => item.id} loading={loading} onRetry={() => void load()} emptyState={<EmptyState title="Henüz ürün yok" description="İlk maliyet ürününü oluşturun." />} /></section> : null}
    {categoryEditing !== undefined ? <FormModal title={categoryEditing ? "Kategoriyi Düzenle" : "Yeni Kategori"} onClose={() => setCategoryEditing(undefined)}><form className="crm-form" onSubmit={saveCategory}><FormField label="Ad" htmlFor="cost-category-name"><TextInput id="cost-category-name" value={categoryValues.name} onChange={(e) => { const name = e.target.value; setCategoryValues((current) => ({ ...current, name, slug: categorySlugTouched ? current.slug : toSlug(name) })); }} required /></FormField><FormField label="Slug" htmlFor="cost-category-slug"><TextInput id="cost-category-slug" value={categoryValues.slug} onChange={(e) => { setCategorySlugTouched(true); setCategoryValues((current) => ({ ...current, slug: toSlug(e.target.value) })); }} required /></FormField><FormField label="Açıklama" htmlFor="cost-category-description"><TextareaInput id="cost-category-description" value={categoryValues.description ?? ""} onChange={(e) => setCategoryValues({ ...categoryValues, description: e.target.value || null })} /></FormField><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setCategoryEditing(undefined)}>İptal</button><button type="submit" className="btn primary" disabled={saving}>{saving ? "Kaydediliyor…" : "Kaydet"}</button></div></form></FormModal> : null}
    {productEditing !== undefined ? <FormModal title={productEditing ? "Ürünü Düzenle" : "Yeni Ürün"} onClose={() => setProductEditing(undefined)}><form className="crm-form" onSubmit={saveProduct}><FormField label="Kategori" htmlFor="cost-product-category"><select id="cost-product-category" className="form-control" value={productValues.category_id} onChange={(e) => setProductValues({ ...productValues, category_id: e.target.value })} required>{categoryOptions.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></FormField><FormField label="Ad" htmlFor="cost-product-name"><TextInput id="cost-product-name" value={productValues.name} onChange={(e) => { const name = e.target.value; setProductValues((current) => ({ ...current, name, slug: productSlugTouched ? current.slug : toSlug(name) })); }} required /></FormField><FormField label="Slug" htmlFor="cost-product-slug"><TextInput id="cost-product-slug" value={productValues.slug} onChange={(e) => { setProductSlugTouched(true); setProductValues((current) => ({ ...current, slug: toSlug(e.target.value) })); }} required /></FormField><FormField label="Birim" htmlFor="cost-product-unit"><select id="cost-product-unit" className="form-control" value={productValues.unit} onChange={(e) => setProductValues({ ...productValues, unit: e.target.value as CostUnit })}>{units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select></FormField><FormField label="Birim fiyat" htmlFor="cost-product-price"><TextInput id="cost-product-price" type="number" min="0" step="0.0001" value={productValues.unit_price} onChange={(e) => setProductValues({ ...productValues, unit_price: e.target.value })} required /></FormField><FormField label="Para birimi" htmlFor="cost-product-currency"><select id="cost-product-currency" className="form-control" value={productValues.currency} onChange={(e) => setProductValues({ ...productValues, currency: e.target.value as CostCurrency })}>{currencies.map((currency) => <option key={currency} value={currency}>{currency}</option>)}</select></FormField><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setProductEditing(undefined)}>İptal</button><button type="submit" className="btn primary" disabled={saving}>{saving ? "Kaydediliyor…" : "Kaydet"}</button></div></form></FormModal> : null}
  </PageShell>;
}
