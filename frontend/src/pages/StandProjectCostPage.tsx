import React from "react";
import { ApiError } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { TableRowActions } from "../components/ui/TableRowActions";
import { FormField, SelectInput, TextInput } from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { loadStandProjectCost, type LoadedStandProjectCost } from "../domain/loadStandProjectCost";
import {
  buildStandProjectCostSheet,
  formatCostMoney,
  formatCostQuantity,
  manualCostItemChoices,
  parsePositiveQuantity,
  removeManualCostItem,
  selectManualCostItem,
  sortCostSheetRows,
  type CostSheetRow,
  type ManualCostEntry,
} from "../domain/standProjectCost";
import { standProjectCostLabels, standProjectsLabels } from "../labels/standProjectsLabels";
import { getGrantedCorePermissions, hasGrantedCorePermission } from "../permissions/corePermissions";
import { PERMISSION_COST_ITEMS_READ, PERMISSION_STAND_PROJECTS_READ } from "../permissions/navigationPermissions";
import type { SortDirection } from "../types/listTable";

type StandProjectCostPageProps = {
  projectId: string;
  onBack: () => void;
};

function moneyCell(value: number | null): string {
  return value == null ? standProjectCostLabels.noTotal : formatCostMoney(value);
}

function missingPriceCell(): React.ReactNode {
  return <Badge variant="neutral">{standProjectCostLabels.missingPrice}</Badge>;
}

function matchesCostSearch(row: CostSheetRow, search: string): boolean {
  const query = search.trim().toLocaleLowerCase("tr-TR");
  if (!query) return true;
  const source = row.source === "BOM" ? standProjectCostLabels.sourceBom : standProjectCostLabels.sourceManual;
  return [row.name, source, row.unitLabel].join(" ").toLocaleLowerCase("tr-TR").includes(query);
}

export function StandProjectCostPage({ projectId, onBack }: StandProjectCostPageProps) {
  const granted = React.useMemo(() => getGrantedCorePermissions(), []);
  const canRead = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_READ)
    && hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_READ);

  const [loaded, setLoaded] = React.useState<LoadedStandProjectCost | null>(null);
  const [manualEntries, setManualEntries] = React.useState<ManualCostEntry[]>([]);
  const [search, setSearch] = React.useState("");
  const [sorting, setSorting] = React.useState<{ field: string | null; direction: SortDirection | null }>({
    field: null,
    direction: null,
  });
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setManualEntries([]);
    void loadStandProjectCost(projectId)
      .then((result) => {
        if (!cancelled) setLoaded(result);
      })
      .catch((loadError) => {
        if (cancelled) return;
        setLoaded(null);
        setError(
          loadError instanceof ApiError || loadError instanceof Error
            ? loadError.message
            : standProjectCostLabels.loadError,
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [canRead, projectId]);

  const sheet = React.useMemo(() => {
    if (!loaded) return null;
    return buildStandProjectCostSheet({
      bomLines: loaded.bomLines,
      costItems: loaded.costItems,
      manualEntries,
      units: loaded.units,
    });
  }, [loaded, manualEntries]);

  const manualChoices = React.useMemo(
    () => (loaded ? manualCostItemChoices(loaded.costItems) : []),
    [loaded],
  );
  const changeSort = React.useCallback((field: string) => {
    setSorting((current) => ({
      field,
      direction: current.field === field && current.direction === "asc" ? "desc" : "asc",
    }));
  }, []);
  const visibleRows = React.useMemo(() => {
    if (!sheet) return [];
    const filtered = sheet.rows.filter((row) => matchesCostSearch(row, search));
    if (!sorting.field || !sorting.direction) return filtered;
    return sortCostSheetRows(filtered, sorting.field, sorting.direction);
  }, [search, sheet, sorting]);

  const columns = React.useMemo((): UniversalDataTableColumn<CostSheetRow>[] => [
    {
      key: "source",
      title: standProjectCostLabels.colSource,
      sortable: true,
      render: (row) => (row.source === "BOM" ? standProjectCostLabels.sourceBom : standProjectCostLabels.sourceManual),
    },
    {
      key: "name",
      title: standProjectCostLabels.colName,
      sortable: true,
      render: (row) => row.name,
    },
    {
      key: "quantity",
      title: standProjectCostLabels.colQuantity,
      sortable: true,
      render: (row) => {
        if (row.source !== "MANUAL" || !row.manualCostItemId) {
          return row.quantity == null ? standProjectCostLabels.noTotal : formatCostQuantity(row.quantity);
        }
        const entry = manualEntries.find((item) => item.costItemId === row.manualCostItemId);
        const invalid = parsePositiveQuantity(entry?.quantity ?? "") == null;
        return (
          <TextInput
            id={`stand-cost-qty-${row.manualCostItemId}`}
            inputMode="decimal"
            value={entry?.quantity ?? ""}
            aria-invalid={invalid}
            onChange={(event) => {
              const quantity = event.target.value;
              const costItemId = row.manualCostItemId;
              if (!costItemId) return;
              setManualEntries((current) =>
                current.map((item) => (item.costItemId === costItemId ? { ...item, quantity } : item)),
              );
            }}
          />
        );
      },
    },
    {
      key: "unit",
      title: standProjectCostLabels.colUnit,
      sortable: true,
      render: (row) => row.unitLabel,
    },
    {
      key: "purchaseUnit",
      title: standProjectCostLabels.colPurchaseUnit,
      sortable: true,
      render: (row) => (row.purchaseUnit == null ? missingPriceCell() : moneyCell(row.purchaseUnit)),
    },
    {
      key: "purchaseTotal",
      title: standProjectCostLabels.colPurchaseTotal,
      sortable: true,
      render: (row) => moneyCell(row.purchaseTotal),
    },
    {
      key: "saleUnit",
      title: standProjectCostLabels.colSaleUnit,
      sortable: true,
      render: (row) => (row.saleUnit == null ? missingPriceCell() : moneyCell(row.saleUnit)),
    },
    {
      key: "saleTotal",
      title: standProjectCostLabels.colSaleTotal,
      sortable: true,
      render: (row) => moneyCell(row.saleTotal),
    },
    {
      key: "actions",
      title: standProjectsLabels.colActions,
      sortable: false,
      render: (row) => row.source === "MANUAL" && row.manualCostItemId ? (
        <TableRowActions>
          <Button
            size="sm"
            variant="danger"
            onClick={() => setManualEntries((current) => removeManualCostItem(current, row.manualCostItemId as string))}
          >
            {standProjectCostLabels.removeManual}
          </Button>
        </TableRowActions>
      ) : standProjectCostLabels.noTotal,
    },
  ], [manualEntries]);

  const headerActions = React.useMemo((): PageHeaderAction[] => [
    {
      id: "back-stand-projects",
      label: standProjectsLabels.backToList,
      variant: "secondary",
      onClick: onBack,
    },
  ], [onBack]);

  if (!canRead) {
    return (
      <PageShell>
        <PageHeader title={standProjectCostLabels.pageTitle} actions={headerActions} />
        <EmptyState title={standProjectCostLabels.pageTitle} description={standProjectCostLabels.denied} />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title={loaded ? `${standProjectCostLabels.pageTitle} — ${loaded.projectName}` : standProjectCostLabels.pageTitle}
        subtitle={standProjectCostLabels.pageSubtitle}
        actions={headerActions}
      />
      {loading ? <LoadingState message={standProjectCostLabels.loading} /> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
      {!loading && !error && sheet && sheet.totals.unpricedBomCount > 0 ? (
        <Banner variant="warning">{standProjectCostLabels.missingPriceNotice(sheet.totals.unpricedBomCount)}</Banner>
      ) : null}
      {!loading && !error && loaded ? (
        <FilterPanel className="stand-project-cost-toolbar">
          <FormField label={standProjectCostLabels.filterSearch} htmlFor="stand-cost-search">
            <TextInput
              id="stand-cost-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={standProjectCostLabels.filterSearchPlaceholder}
            />
          </FormField>
          <FormField label={standProjectCostLabels.addManual} htmlFor="stand-cost-manual-item">
            <SelectInput
              id="stand-cost-manual-item"
              value=""
              disabled={manualChoices.length === 0}
              onChange={(event) => {
                const costItemId = event.target.value;
                if (!costItemId) return;
                setManualEntries((current) => selectManualCostItem(current, costItemId));
              }}
            >
              <option value="">
                {manualChoices.length === 0 ? standProjectCostLabels.noManualItems : standProjectCostLabels.addManual}
              </option>
              {manualChoices.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </SelectInput>
          </FormField>
        </FilterPanel>
      ) : null}
      {!loading && !error && sheet && sheet.rows.length === 0 ? (
        <EmptyState title={standProjectCostLabels.emptyTitle} description={standProjectCostLabels.emptyDescription} />
      ) : null}
      {!loading && !error && sheet && sheet.rows.length > 0 ? (
        <UniversalDataTable
          columns={columns}
          items={visibleRows}
          rowKey={(row) => row.key}
          sorting={sorting}
          onSortChange={changeSort}
          summary={(
            <div className="stand-project-cost-total-band">
              {([
                [standProjectCostLabels.bandBomPurchase, sheet.totals.bomPurchase],
                [standProjectCostLabels.bandBomSale, sheet.totals.bomSale],
                [standProjectCostLabels.bandManualPurchase, sheet.totals.manualPurchase],
                [standProjectCostLabels.bandManualSale, sheet.totals.manualSale],
                [standProjectCostLabels.bandGrandPurchase, sheet.totals.grandPurchase],
                [standProjectCostLabels.bandGrandSale, sheet.totals.grandSale],
              ] as const).map(([label, amount]) => (
                <span key={label} className="stand-project-cost-total-cell">
                  <span>{label}:</span>
                  <strong>{formatCostMoney(amount)}</strong>
                </span>
              ))}
            </div>
          )}
          emptyState={(
            <EmptyState
              title={standProjectCostLabels.searchEmptyTitle}
              description={standProjectCostLabels.searchEmptyDescription}
            />
          )}
        />
      ) : null}
      {!loading && !error && manualEntries.some((entry) => parsePositiveQuantity(entry.quantity) == null) ? (
        <Banner variant="warning">{standProjectCostLabels.invalidQuantity}</Banner>
      ) : null}
    </PageShell>
  );
}
