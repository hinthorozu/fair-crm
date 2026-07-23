import React from "react";
import { cancelOperation, listOperationTypes, listOperations, startOperation } from "../api/operations";
import { ApiError } from "../api/client";
import { NewOperationTypeModal } from "../components/operations/NewOperationTypeModal";
import { OperationRunStatusBadge } from "../components/operations/OperationRunStatusBadge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { SelectInput, TextInput } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { TableRowActions } from "../components/ui/TableRowActions";
import { TruncatedText } from "../components/ui/TruncatedText";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import {
  operationLabels,
  operationPriorityLabels,
  operationTypeLabels,
} from "../labels/operationLabels";
import type {
  Operation,
  OperationType,
  OperationTypeCatalogItem,
} from "../types/operation";
import { buildCatalogNameMap } from "../utils/operationWizardTypes";
import {
  operationUserFacingStatusFilterOptions,
  resolveOperationUserFacingStatus,
} from "../utils/operationRunStatus";

interface OperationsPageProps {
  onOpenDetail: (operationId: string) => void;
  onSelectType: (type: OperationType) => void;
}

function formatProgress(operation: Operation): string {
  const run = operation.latest_run;
  if (!run) return "—";
  const pct = Math.round((run.progress ?? 0) * 100);
  return `${pct}% (${run.processed_items}/${run.total_items})`;
}

export function OperationsPage({ onOpenDetail, onSelectType }: OperationsPageProps) {
  const [banner, setBanner] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [typeModalOpen, setTypeModalOpen] = React.useState(false);
  const [typeCatalog, setTypeCatalog] = React.useState<OperationTypeCatalogItem[]>([]);

  const table = useServerDataTable<Operation>({
    fetchFn: (params) =>
      listOperations({
        ...params,
        operation_type: params.filters.operation_type || undefined,
        status: params.filters.status || undefined,
      }),
    defaultSort: { field: "created_at", direction: "desc" },
    filterKeys: ["operation_type", "status"],
    urlSync: true,
    urlPath: "/operations",
  });

  React.useEffect(() => {
    let cancelled = false;
    void listOperationTypes({ activeOnly: true })
      .then((response) => {
        if (!cancelled) setTypeCatalog(response.items);
      })
      .catch(() => {
        if (!cancelled) setTypeCatalog([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const typeNameByKey = React.useMemo(() => buildCatalogNameMap(typeCatalog), [typeCatalog]);

  React.useEffect(() => {
    if (!banner) return undefined;
    const timer = window.setTimeout(() => setBanner(null), 5000);
    return () => window.clearTimeout(timer);
  }, [banner]);

  const handleStart = async (operation: Operation) => {
    setBusyId(operation.id);
    setActionError(null);
    try {
      await startOperation(operation.id);
      setBanner(operationLabels.startSuccess);
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setBusyId(null);
    }
  };

  const handleCancel = async (operation: Operation) => {
    setBusyId(operation.id);
    setActionError(null);
    try {
      await cancelOperation(operation.id);
      setBanner(operationLabels.cancelSuccess);
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : operationLabels.loadError);
    } finally {
      setBusyId(null);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<Operation>[]>(
    () => [
      {
        key: "title",
        title: operationLabels.colTitle,
        sortField: "title",
        priority: "primary",
        allowWrap: true,
        render: (item) => (
          <TableEntityLink onClick={() => onOpenDetail(item.id)}>
            <TruncatedText value={item.title} />
          </TableEntityLink>
        ),
      },
      {
        key: "operation_type",
        title: operationLabels.colType,
        sortField: "operation_type",
        priority: "primary",
        render: (item) =>
          typeNameByKey.get(item.operation_type) ??
          operationTypeLabels[item.operation_type as OperationType] ??
          item.operation_type,
      },
      {
        key: "status",
        title: operationLabels.colStatus,
        sortable: false,
        priority: "primary",
        render: (item) => (
          <OperationRunStatusBadge status={resolveOperationUserFacingStatus(item)} />
        ),
      },
      {
        key: "priority",
        title: operationLabels.colPriority,
        sortField: "priority",
        priority: "secondary",
        render: (item) =>
          operationPriorityLabels[item.priority as keyof typeof operationPriorityLabels] ??
          item.priority,
      },
      {
        key: "progress",
        title: operationLabels.colProgress,
        sortable: false,
        priority: "secondary",
        render: (item) => formatProgress(item),
      },
      {
        key: "updated_at",
        title: operationLabels.colUpdatedAt,
        sortField: "updated_at",
        priority: "secondary",
        render: (item) => new Date(item.updated_at).toLocaleString("tr-TR"),
      },
      {
        key: "actions",
        title: operationLabels.colActions,
        sortable: false,
        priority: "primary",
        className: "actions",
        render: (item) => {
          const loading = busyId === item.id;
          return (
            <TableRowActions>
              <button
                type="button"
                className="btn link"
                onClick={() => onOpenDetail(item.id)}
              >
                {operationLabels.actionOpen}
              </button>
              {["draft", "ready", "active"].includes(item.status) ? (
                <button
                  type="button"
                  className="btn link"
                  disabled={loading}
                  onClick={() => void handleStart(item)}
                >
                  {operationLabels.actionStart}
                </button>
              ) : null}
              {["draft", "ready", "active"].includes(item.status) ? (
                <button
                  type="button"
                  className="btn link danger"
                  disabled={loading}
                  onClick={() => void handleCancel(item)}
                >
                  {operationLabels.actionCancel}
                </button>
              ) : null}
            </TableRowActions>
          );
        },
      },
    ],
    [busyId, onOpenDetail, typeNameByKey],
  );

  const statusFilterOptions = React.useMemo(
    () => operationUserFacingStatusFilterOptions(),
    [],
  );

  return (
    <PageShell className="operations-page">
      <PageHeader
        title={operationLabels.pageTitle}
        subtitle={`${table.pagination.totalItems} kayıt`}
        actions={
          <Button type="button" variant="primary" onClick={() => setTypeModalOpen(true)}>
            {operationLabels.newOperation}
          </Button>
        }
      />
      <NewOperationTypeModal
        open={typeModalOpen}
        onClose={() => setTypeModalOpen(false)}
        onContinue={(type) => {
          setTypeModalOpen(false);
          onSelectType(type);
        }}
      />
      {banner ? <Banner variant="success">{banner}</Banner> : null}
      {actionError ? <Banner variant="error">{actionError}</Banner> : null}

      <UniversalDataTable
        table={table}
        rowKey={(row) => row.id}
        columns={columns}
        skeletonCols={7}
        emptyState={
          <EmptyState
            title={
              table.hasActiveFilters
                ? operationLabels.emptyFilteredTitle
                : operationLabels.emptyTitle
            }
            description={
              table.hasActiveFilters
                ? operationLabels.emptyFilteredDescription
                : operationLabels.emptyDescription
            }
          />
        }
        toolbar={
          <FilterPanel
            actions={
              <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
                Yenile
              </button>
            }
          >
            <TextInput
              id="operation-search"
              type="search"
              className="search-input"
              placeholder={operationLabels.searchPlaceholder}
              value={table.search}
              onChange={(event) => table.setSearch(event.target.value)}
              aria-label={operationLabels.searchPlaceholder}
            />
            <SelectInput
              id="operation-filter-type"
              value={table.filters.operation_type ?? ""}
              onChange={(event) => table.setFilter("operation_type", event.target.value)}
              aria-label={operationLabels.filterType}
            >
              <option value="">{operationLabels.filterAll}</option>
              {typeCatalog.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))}
            </SelectInput>
            <SelectInput
              id="operation-filter-status"
              value={table.filters.status ?? ""}
              onChange={(event) => table.setFilter("status", event.target.value)}
              aria-label={operationLabels.filterStatus}
            >
              <option value="">{operationLabels.filterAll}</option>
              {statusFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectInput>
          </FilterPanel>
        }
      />
    </PageShell>
  );
}
