import React from "react";
import { ApiError } from "../api/client";
import {
  calculationUnitLabel,
  createFairStandCostItem,
  deleteFairStandCostItem,
  listFairStandCostItemFormCatalog,
  listFairStandCostItems,
  updateFairStandCostItem,
  type FairStandCostItem,
  type FairStandCostItemOption,
  type FairStandCostItemType,
  type FairStandUnitOption,
} from "../api/fairStandCostItems";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { TableRowActions } from "../components/ui/TableRowActions";
import { FormField, SelectInput, TextInput } from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { costItemsLabels } from "../labels/costItemsLabels";
import { getGrantedCorePermissions, hasGrantedCorePermission } from "../permissions/corePermissions";
import {
  PERMISSION_COST_ITEMS_CREATE,
  PERMISSION_COST_ITEMS_DELETE,
  PERMISSION_COST_ITEMS_READ,
  PERMISSION_COST_ITEMS_UPDATE,
} from "../permissions/navigationPermissions";

export function costItemOptionsForForm(
  options: FairStandCostItemOption[],
  pricedItemKeys: string[],
  editingItemKey: string | null,
): FairStandCostItemOption[] {
  if (editingItemKey) return options.filter((option) => option.itemKey === editingItemKey);
  const priced = new Set(pricedItemKeys);
  return options.filter((option) => !priced.has(option.itemKey));
}

export function costItemFormFields(type: FairStandCostItemType): {
  item: boolean;
  name: boolean;
  unit: boolean;
} {
  if (type === "MANUAL") return { item: false, name: true, unit: true };
  return { item: true, name: false, unit: false };
}

export function costItemFormError(
  purchaseRaw: string,
  saleRaw: string,
  entry: { type?: FairStandCostItemType; name?: string; unitKey?: string } = {},
): string | null {
  if ((entry.type ?? "ITEM") === "MANUAL") {
    if (!entry.name?.trim()) return costItemsLabels.nameRequired;
    if (!entry.unitKey?.trim()) return costItemsLabels.unitRequired;
  }
  const purchase = purchaseRaw.trim().replace(",", ".");
  const sale = saleRaw.trim().replace(",", ".");
  if (!purchase) return costItemsLabels.purchaseRequired;
  if (!/^\d+(\.\d{1,2})?$/.test(purchase)) return costItemsLabels.purchaseInvalid;
  if (sale && !/^\d+(\.\d{1,2})?$/.test(sale)) return costItemsLabels.saleInvalid;
  return null;
}

function moneyForApi(raw: string): string {
  const normalized = raw.trim().replace(",", ".");
  const [whole, fraction = ""] = normalized.split(".");
  return `${whole}.${fraction.padEnd(2, "0")}`;
}

export function StandCostItemsPage() {
  const granted = React.useMemo(() => getGrantedCorePermissions(), []);
  const canRead = hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_READ);
  const canCreate = hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_CREATE);
  const canUpdate = hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_UPDATE);
  const canDelete = hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_DELETE);

  const [prices, setPrices] = React.useState<FairStandCostItem[]>([]);
  const [options, setOptions] = React.useState<FairStandCostItemOption[]>([]);
  const [units, setUnits] = React.useState<FairStandUnitOption[]>([]);
  const [entryType, setEntryType] = React.useState<FairStandCostItemType>("ITEM");
  const [manualName, setManualName] = React.useState("");
  const [unitKey, setUnitKey] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<FairStandCostItem | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [itemKey, setItemKey] = React.useState("");
  const [purchasePrice, setPurchasePrice] = React.useState("");
  const [salePrice, setSalePrice] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState<FairStandCostItem | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const names = React.useMemo(() => {
    const map = new Map(options.map((option) => [option.itemKey, option.name]));
    return map;
  }, [options]);

  const unitNames = React.useMemo(() => {
    const map = new Map(options.map((option) => [option.itemKey, option.unitName]));
    return map;
  }, [options]);

  const dropdownOptions = React.useMemo(
    () =>
      costItemOptionsForForm(
        options,
        prices.filter((row) => row.costItemType !== "MANUAL").map((row) => row.itemKey ?? ""),
        editing?.itemKey ?? null,
      ),
    [editing, options, prices],
  );

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, catalog] = await Promise.all([
        listFairStandCostItems(),
        listFairStandCostItemFormCatalog(),
      ]);
      setPrices(rows);
      setOptions(catalog.items);
      setUnits(catalog.units);
    } catch (loadError) {
      setError(
        loadError instanceof ApiError || loadError instanceof Error
          ? loadError.message
          : costItemsLabels.loadError,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const closeForm = () => {
    setCreating(false);
    setEditing(null);
    setEntryType("ITEM");
    setItemKey("");
    setManualName("");
    setUnitKey("");
    setPurchasePrice("");
    setSalePrice("");
    setFormError(null);
  };

  const openCreate = () => {
    if (!canCreate) return;
    setEditing(null);
    setCreating(true);
    setEntryType("ITEM");
    setItemKey("");
    setManualName("");
    setUnitKey("");
    setPurchasePrice("");
    setSalePrice("");
    setFormError(null);
  };

  const openEdit = (row: FairStandCostItem) => {
    if (!canUpdate) return;
    setCreating(false);
    setEditing(row);
    setEntryType(row.costItemType);
    setItemKey(row.itemKey ?? "");
    setManualName(row.name ?? "");
    setUnitKey(row.unit ?? "");
    setPurchasePrice(row.purchasePrice);
    setSalePrice(row.salePrice === "0.00" ? "" : row.salePrice);
    setFormError(null);
  };

  const save = async () => {
    const validation = costItemFormError(purchasePrice, salePrice, {
      type: entryType,
      name: manualName,
      unitKey,
    });
    if (validation) {
      setFormError(validation);
      return;
    }
    setSaving(true);
    setError(null);
    setFormError(null);
    try {
      const purchase = moneyForApi(purchasePrice);
      const sale = salePrice.trim() ? moneyForApi(salePrice) : null;
      if (editing && canUpdate) {
        await updateFairStandCostItem(editing.id, {
          purchasePrice: purchase,
          salePrice: sale,
          ...(editing.costItemType === "MANUAL" ? { name: manualName.trim(), unit: unitKey } : {}),
        });
      } else if (canCreate && entryType === "MANUAL") {
        await createFairStandCostItem({
          costItemType: "MANUAL",
          name: manualName.trim(),
          unit: unitKey,
          purchasePrice: purchase,
          ...(sale ? { salePrice: sale } : {}),
        });
      } else if (canCreate) {
        await createFairStandCostItem({
          costItemType: "ITEM",
          itemKey,
          purchasePrice: purchase,
          ...(sale ? { salePrice: sale } : {}),
        });
      }
      closeForm();
      await load();
    } catch (saveError) {
      setError(
        saveError instanceof ApiError || saveError instanceof Error
          ? saveError.message
          : costItemsLabels.saveError,
      );
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!canDelete || !deleting) return;
    setDeleteBusy(true);
    setError(null);
    try {
      await deleteFairStandCostItem(deleting.id);
      setDeleting(null);
      await load();
    } catch (deleteError) {
      setError(
        deleteError instanceof ApiError || deleteError instanceof Error
          ? deleteError.message
          : costItemsLabels.deleteError,
      );
    } finally {
      setDeleteBusy(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<FairStandCostItem>[]>(() => {
    const cols: UniversalDataTableColumn<FairStandCostItem>[] = [
      {
        key: "type",
        title: costItemsLabels.colType,
        sortable: false,
        render: (row) => (row.costItemType === "MANUAL" ? costItemsLabels.typeManual : costItemsLabels.typeItem),
      },
      {
        key: "item",
        title: costItemsLabels.colItem,
        sortable: false,
        render: (row) =>
          row.costItemType === "MANUAL" ? (row.name ?? "") : (names.get(row.itemKey ?? "") ?? row.itemKey ?? ""),
      },
      {
        key: "unit",
        title: costItemsLabels.colUnit,
        sortable: false,
        render: (row) =>
          row.costItemType === "MANUAL"
            ? calculationUnitLabel(row.unit, units)
            : (unitNames.get(row.itemKey ?? "") ?? ""),
      },
      {
        key: "purchase",
        title: costItemsLabels.colPurchase,
        sortable: false,
        render: (row) => row.purchasePrice,
      },
      {
        key: "sale",
        title: costItemsLabels.colSale,
        sortable: false,
        render: (row) => row.salePrice,
      },
    ];
    if (canUpdate || canDelete) {
      cols.push({
        key: "actions",
        title: costItemsLabels.colActions,
        sortable: false,
        render: (row) => (
          <TableRowActions>
            {canUpdate ? (
              <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>
                {costItemsLabels.actionEdit}
              </Button>
            ) : null}
            {canDelete ? (
              <Button size="sm" variant="danger" onClick={() => setDeleting(row)}>
                {costItemsLabels.actionDelete}
              </Button>
            ) : null}
          </TableRowActions>
        ),
      });
    }
    return cols;
  }, [canDelete, canUpdate, names, unitNames, units]);

  if (!canRead) {
    return (
      <PageShell>
        <PageHeader title={costItemsLabels.pageTitle} />
        <EmptyState title={costItemsLabels.pageTitle} description={costItemsLabels.denied} />
      </PageShell>
    );
  }

  const headerActions: PageHeaderAction[] = canCreate
    ? [{ id: "create-cost-item", label: costItemsLabels.actionCreate, onClick: openCreate, variant: "primary" }]
    : [];
  const formOpen = creating || editing !== null;
  const fields = costItemFormFields(entryType);
  const saveDisabled =
    saving || (creating && fields.item && !itemKey) || (creating && fields.name && !manualName.trim()) || (creating && fields.unit && !unitKey);

  return (
    <PageShell>
      <PageHeader
        title={costItemsLabels.pageTitle}
        subtitle={costItemsLabels.pageSubtitle}
        actions={headerActions}
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {formOpen && (creating ? canCreate : canUpdate) ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          {formError ? <Banner variant="error">{formError}</Banner> : null}
          <FormField label={costItemsLabels.fieldType} htmlFor="cost-item-type">
            <SelectInput
              id="cost-item-type"
              value={entryType}
              disabled={Boolean(editing) || saving}
              onChange={(event) => {
                const next = event.target.value === "MANUAL" ? "MANUAL" : "ITEM";
                setEntryType(next);
                setFormError(null);
              }}
            >
              <option value="ITEM">{costItemsLabels.typeItem}</option>
              <option value="MANUAL">{costItemsLabels.typeManual}</option>
            </SelectInput>
          </FormField>
          {fields.item ? (
            <FormField label={costItemsLabels.fieldItem} htmlFor="cost-item-item">
              <SelectInput
                id="cost-item-item"
                value={itemKey}
                disabled={Boolean(editing) || saving}
                onChange={(event) => setItemKey(event.target.value)}
              >
                <option value="">{costItemsLabels.fieldItem}</option>
                {dropdownOptions.map((option) => (
                  <option key={option.itemKey} value={option.itemKey}>
                    {option.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          ) : null}
          {creating && fields.item && dropdownOptions.length === 0 ? (
            <p>{options.length === 0 ? costItemsLabels.noItems : costItemsLabels.noRemainingItems}</p>
          ) : null}
          {fields.name ? (
            <FormField label={costItemsLabels.fieldName} htmlFor="cost-item-name">
              <TextInput
                id="cost-item-name"
                value={manualName}
                disabled={saving}
                onChange={(event) => setManualName(event.target.value)}
              />
            </FormField>
          ) : null}
          {fields.unit ? (
            <FormField label={costItemsLabels.fieldUnit} htmlFor="cost-item-unit">
              <SelectInput
                id="cost-item-unit"
                value={unitKey}
                disabled={saving}
                onChange={(event) => setUnitKey(event.target.value)}
              >
                <option value="">{costItemsLabels.fieldUnit}</option>
                {units.map((unit) => (
                  <option key={unit.unitKey} value={unit.unitKey}>
                    {unit.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          ) : null}
          <FormField label={costItemsLabels.fieldPurchase} htmlFor="cost-item-purchase">
            <TextInput
              id="cost-item-purchase"
              inputMode="decimal"
              value={purchasePrice}
              disabled={saving}
              onChange={(event) => setPurchasePrice(event.target.value)}
            />
          </FormField>
          <FormField label={costItemsLabels.fieldSale} htmlFor="cost-item-sale">
            <TextInput
              id="cost-item-sale"
              inputMode="decimal"
              value={salePrice}
              disabled={saving}
              onChange={(event) => setSalePrice(event.target.value)}
            />
          </FormField>
          <Button type="submit" variant="primary" disabled={saveDisabled}>
            {costItemsLabels.actionSave}
          </Button>
          <Button type="button" variant="secondary" disabled={saving} onClick={closeForm}>
            {costItemsLabels.actionCancel}
          </Button>
        </form>
      ) : null}
      {loading ? <LoadingState /> : null}
      {!loading && prices.length === 0 ? (
        <EmptyState title={costItemsLabels.emptyTitle} description={costItemsLabels.emptyDescription} />
      ) : null}
      {!loading && prices.length > 0 ? (
        <UniversalDataTable columns={columns} items={prices} rowKey={(row) => row.id} />
      ) : null}
      {deleting && canDelete ? (
        <ConfirmDialog
          title={costItemsLabels.deleteTitle}
          message={costItemsLabels.deleteMessage}
          variant="danger"
          loading={deleteBusy}
          confirmLabel={costItemsLabels.actionDelete}
          onConfirm={() => void confirmDelete()}
          onCancel={() => {
            if (!deleteBusy) setDeleting(null);
          }}
        />
      ) : null}
    </PageShell>
  );
}
