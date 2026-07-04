import type { AdapterDetail, AdapterListItem } from "../types/scraper";

export function adapterDetailToListItem(detail: AdapterDetail): AdapterListItem {
  return {
    id: detail.id,
    adapter_key: detail.adapter_key,
    engine_key: detail.engine_key,
    engine_type: detail.engine_type,
    display_name: detail.name,
    version: detail.version,
    features: detail.features,
    last_verified: detail.last_verified,
    actions_available: detail.actions_available,
    description: detail.description,
    is_active: detail.is_active,
    is_registered: detail.is_registered,
  };
}

export function mergeAdapterListItem(
  items: AdapterListItem[],
  nextItem: AdapterListItem,
): AdapterListItem[] {
  const without = items.filter((item) => item.adapter_key !== nextItem.adapter_key);
  return [...without, nextItem];
}
