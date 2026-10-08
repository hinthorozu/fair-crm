import type { FairStandCostItem } from "../api/fairStandCostItems";
import { calculationUnitLabel } from "../api/fairStandCostItems";

export type BomCostSourceLine = {
  itemKey: string;
  name: string;
  quantity: number;
  unit: string;
};

export type ManualCostEntry = {
  costItemId: string;
  quantity: string;
};

export type CostSheetRow = {
  key: string;
  source: "BOM" | "MANUAL";
  name: string;
  quantity: number | null;
  unitLabel: string;
  purchaseUnit: number | null;
  purchaseTotal: number | null;
  saleUnit: number | null;
  saleTotal: number | null;
  manualCostItemId?: string;
};

export type CostTotals = {
  bomPurchase: number;
  bomSale: number;
  manualPurchase: number;
  manualSale: number;
  grandPurchase: number;
  grandSale: number;
  unpricedBomCount: number;
};

type UnitName = { unitKey?: string; name?: string };

export function parsePositiveQuantity(raw: string): number | null {
  const normalized = raw.trim().replace(",", ".");
  if (!normalized) return null;
  const value = Number(normalized);
  if (!Number.isFinite(value) || value <= 0) return null;
  return value;
}

export function formatCostMoney(value: number): string {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatCostQuantity(value: number): string {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 4 }).format(value);
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function roundQuantity(value: number): number {
  return Math.round((value + Number.EPSILON) * 10000) / 10000;
}

function moneyAmount(raw: string | null | undefined): number | null {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const value = Number(raw);
  if (!Number.isFinite(value)) return null;
  return value;
}

function lineTotal(quantity: number, unitPrice: number | null): number | null {
  if (unitPrice == null) return null;
  return roundMoney(quantity * unitPrice);
}

export function manualCostItemChoices(items: FairStandCostItem[]): FairStandCostItem[] {
  return items.filter((item) => item.costItemType === "MANUAL");
}

export function selectManualCostItem(entries: ManualCostEntry[], costItemId: string): ManualCostEntry[] {
  const index = entries.findIndex((entry) => entry.costItemId === costItemId);
  if (index < 0) return [...entries, { costItemId, quantity: "1" }];
  return entries.map((entry, entryIndex) => {
    if (entryIndex !== index) return entry;
    const current = parsePositiveQuantity(entry.quantity) ?? 0;
    return { ...entry, quantity: String(roundQuantity(current + 1)) };
  });
}

export function removeManualCostItem(entries: ManualCostEntry[], costItemId: string): ManualCostEntry[] {
  return entries.filter((entry) => entry.costItemId !== costItemId);
}

function itemCostByKey(items: FairStandCostItem[]): Map<string, FairStandCostItem> {
  const map = new Map<string, FairStandCostItem>();
  for (const item of items) {
    if (item.costItemType !== "ITEM" || !item.itemKey) continue;
    map.set(item.itemKey, item);
  }
  return map;
}

function pricedSide(quantity: number, rawPrice: string | null | undefined): { unit: number | null; total: number | null } {
  const unit = moneyAmount(rawPrice);
  return { unit, total: lineTotal(quantity, unit) };
}

export function buildStandProjectCostSheet(input: {
  bomLines: BomCostSourceLine[];
  costItems: FairStandCostItem[];
  manualEntries: ManualCostEntry[];
  units: UnitName[];
}): { rows: CostSheetRow[]; totals: CostTotals } {
  const priced = itemCostByKey(input.costItems);
  const manuals = new Map(
    manualCostItemChoices(input.costItems).map((item) => [item.id, item] as const),
  );
  const rows: CostSheetRow[] = [];

  for (const entry of input.manualEntries) {
    const cost = manuals.get(entry.costItemId);
    if (!cost) continue;
    const quantity = parsePositiveQuantity(entry.quantity);
    const purchase = quantity == null ? { unit: moneyAmount(cost.purchasePrice), total: null } : pricedSide(quantity, cost.purchasePrice);
    const sale = quantity == null ? { unit: moneyAmount(cost.salePrice), total: null } : pricedSide(quantity, cost.salePrice);
    rows.push({
      key: `manual:${cost.id}`,
      source: "MANUAL",
      name: cost.name?.trim() || cost.id,
      quantity,
      unitLabel: calculationUnitLabel(cost.unit, input.units),
      purchaseUnit: purchase.unit,
      purchaseTotal: purchase.total,
      saleUnit: sale.unit,
      saleTotal: sale.total,
      manualCostItemId: cost.id,
    });
  }

  for (const line of input.bomLines) {
    const cost = priced.get(line.itemKey);
    const purchase = cost ? pricedSide(line.quantity, cost.purchasePrice) : { unit: null, total: null };
    const sale = cost ? pricedSide(line.quantity, cost.salePrice) : { unit: null, total: null };
    rows.push({
      key: `bom:${line.itemKey}:${rows.length}`,
      source: "BOM",
      name: line.name || line.itemKey,
      quantity: line.quantity,
      unitLabel: calculationUnitLabel(line.unit, input.units),
      purchaseUnit: purchase.unit,
      purchaseTotal: purchase.total,
      saleUnit: sale.unit,
      saleTotal: sale.total,
    });
  }

  const ordered = [
    ...rows.filter((row) => row.purchaseUnit != null || row.saleUnit != null),
    ...rows.filter((row) => row.purchaseUnit == null && row.saleUnit == null),
  ];

  const totals = ordered.reduce<CostTotals>(
    (sum, row) => {
      const unpriced = row.source === "BOM" && row.purchaseUnit == null && row.saleUnit == null;
      const next = {
        ...sum,
        unpricedBomCount: sum.unpricedBomCount + (unpriced ? 1 : 0),
      };
      if (row.purchaseTotal == null && row.saleTotal == null) return next;
      if (row.source === "BOM") {
        next.bomPurchase = row.purchaseTotal == null ? next.bomPurchase : roundMoney(next.bomPurchase + row.purchaseTotal);
        next.bomSale = row.saleTotal == null ? next.bomSale : roundMoney(next.bomSale + row.saleTotal);
      } else {
        next.manualPurchase = row.purchaseTotal == null ? next.manualPurchase : roundMoney(next.manualPurchase + row.purchaseTotal);
        next.manualSale = row.saleTotal == null ? next.manualSale : roundMoney(next.manualSale + row.saleTotal);
      }
      next.grandPurchase = roundMoney(next.bomPurchase + next.manualPurchase);
      next.grandSale = roundMoney(next.bomSale + next.manualSale);
      return next;
    },
    {
      bomPurchase: 0,
      bomSale: 0,
      manualPurchase: 0,
      manualSale: 0,
      grandPurchase: 0,
      grandSale: 0,
      unpricedBomCount: 0,
    },
  );

  return { rows: ordered, totals };
}

export function sortCostSheetRows(
  rows: CostSheetRow[],
  field: string,
  direction: "asc" | "desc",
): CostSheetRow[] {
  return rows
    .map((row, index) => ({ row, index }))
    .sort((left, right) => {
      const primary = compareCostSheetField(left.row, right.row, field, direction);
      if (primary !== 0) return primary;
      return left.index - right.index;
    })
    .map((entry) => entry.row);
}

function compareCostSheetField(
  left: CostSheetRow,
  right: CostSheetRow,
  field: string,
  direction: "asc" | "desc",
): number {
  if (field === "quantity") return compareNullableNumber(left.quantity, right.quantity, direction);
  if (field === "purchaseUnit") return compareNullableNumber(left.purchaseUnit, right.purchaseUnit, direction);
  if (field === "purchaseTotal") return compareNullableNumber(left.purchaseTotal, right.purchaseTotal, direction);
  if (field === "saleUnit") return compareNullableNumber(left.saleUnit, right.saleUnit, direction);
  if (field === "saleTotal") return compareNullableNumber(left.saleTotal, right.saleTotal, direction);
  if (field === "source") return compareText(left.source, right.source, direction);
  if (field === "unit") return compareText(left.unitLabel, right.unitLabel, direction);
  if (field === "name") return compareText(left.name, right.name, direction);
  return 0;
}

function compareText(left: string, right: string, direction: "asc" | "desc"): number {
  const result = left.localeCompare(right, "tr", { sensitivity: "base", numeric: true });
  return direction === "asc" ? result : -result;
}

function compareNullableNumber(
  left: number | null,
  right: number | null,
  direction: "asc" | "desc",
): number {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  const result = left - right;
  return direction === "asc" ? result : -result;
}
