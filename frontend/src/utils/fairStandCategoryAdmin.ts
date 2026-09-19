export function nextCatalogIndex(categories: readonly { catalogIndex: number }[]): string {
  const max = categories.reduce((highest, category) => Math.max(highest, category.catalogIndex), 0);
  return String(max + 1);
}

export function categorySaveErrorMessage(raw: string): string {
  if (raw.includes("catalog_index already exists")) {
    return "Bu sıra numarası zaten kullanılıyor.";
  }
  return raw;
}

export function categoryWritePayload(form: {
  catalog_name: string;
  catalog_index: string;
  is_active: boolean;
}) {
  return {
    catalog_name: form.catalog_name.trim(),
    catalog_index: Number(form.catalog_index),
    is_active: form.is_active,
  };
}
