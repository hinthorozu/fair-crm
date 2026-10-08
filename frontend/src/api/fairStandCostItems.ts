import { apiRequest } from "./client";

const base = "/api/v1/fair-stand/cost-items";

export type FairStandCostItemType = "ITEM" | "MANUAL";

export type FairStandCostItem = {
  id: string;
  organizationId: string;
  costItemType: FairStandCostItemType;
  itemKey: string | null;
  name: string | null;
  unit: string | null;
  purchasePrice: string;
  salePrice: string;
  createdAt: number;
  updatedAt: number;
};

export type FairStandUnitOption = {
  unitKey: string;
  name: string;
};

export type FairStandCostItemOption = {
  itemKey: string;
  name: string;
  unitName: string;
};

type ListCostItemsResponse = {
  prices: FairStandCostItem[];
};

type BootstrapResponse = {
  items?: Array<{ itemKey?: string; name?: string; isCostEnabled?: boolean; unit?: string | null }>;
  units?: Array<{ unitKey?: string; name?: string }>;
};

export function calculationUnitLabel(
  unitKey: string | null | undefined,
  units: Array<{ unitKey?: string; name?: string }>,
): string {
  if (typeof unitKey !== "string" || !unitKey) return "";
  const match = units.find((unit) => unit.unitKey === unitKey);
  const name = typeof match?.name === "string" ? match.name.trim() : "";
  return name || unitKey;
}

export function listFairStandCostItems(): Promise<FairStandCostItem[]> {
  return apiRequest<ListCostItemsResponse>(base).then((body) =>
    Array.isArray(body?.prices) ? body.prices : [],
  );
}

function unitOptions(units: BootstrapResponse["units"]): FairStandUnitOption[] {
  return (Array.isArray(units) ? units : [])
    .filter((unit) => typeof unit.unitKey === "string" && unit.unitKey)
    .map((unit) => ({
      unitKey: unit.unitKey as string,
      name: typeof unit.name === "string" && unit.name.trim() ? unit.name.trim() : (unit.unitKey as string),
    }))
    .sort((left, right) => left.name.localeCompare(right.name, "tr"));
}

export function listFairStandCostItemFormCatalog(): Promise<{
  items: FairStandCostItemOption[];
  units: FairStandUnitOption[];
}> {
  return apiRequest<BootstrapResponse>("/api/v1/fair-stand/catalog/bootstrap").then((body) => {
    const items = Array.isArray(body?.items) ? body.items : [];
    const units = Array.isArray(body?.units) ? body.units : [];
    return {
      items: items
        .filter((item) => item.isCostEnabled === true && typeof item.itemKey === "string" && item.itemKey)
        .map((item) => ({
          itemKey: item.itemKey as string,
          name: typeof item.name === "string" && item.name.trim() ? item.name : (item.itemKey as string),
          unitName: calculationUnitLabel(item.unit, units),
        }))
        .sort((left, right) => left.name.localeCompare(right.name, "tr")),
      units: unitOptions(units),
    };
  });
}

export function listFairStandCostItemOptions(): Promise<FairStandCostItemOption[]> {
  return listFairStandCostItemFormCatalog().then((catalog) => catalog.items);
}

export function createFairStandCostItem(input: {
  costItemType: FairStandCostItemType;
  itemKey?: string;
  name?: string;
  unit?: string;
  purchasePrice: string;
  salePrice?: string;
}): Promise<FairStandCostItem> {
  const body: Record<string, string> = {
    costItemType: input.costItemType,
    purchasePrice: input.purchasePrice,
  };
  if (input.costItemType === "ITEM" && input.itemKey) body.itemKey = input.itemKey;
  if (input.costItemType === "MANUAL") {
    if (input.name) body.name = input.name;
    if (input.unit) body.unit = input.unit;
  }
  if (input.salePrice) body.salePrice = input.salePrice;
  return apiRequest<FairStandCostItem>(base, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateFairStandCostItem(
  priceId: string,
  input: { purchasePrice: string; salePrice: string | null; name?: string; unit?: string },
): Promise<FairStandCostItem> {
  return apiRequest<FairStandCostItem>(`${base}/${encodeURIComponent(priceId)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteFairStandCostItem(priceId: string): Promise<void> {
  return apiRequest<void>(`${base}/${encodeURIComponent(priceId)}`, { method: "DELETE" });
}
