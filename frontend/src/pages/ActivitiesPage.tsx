import React from "react";
import {
  bulkDeleteActivities,
  deleteActivity,
  listActivities,
} from "../api/activities";
import { listCustomers } from "../api/customers";
import { ApiError } from "../api/client";
import { ActivityDetailModal } from "../components/ActivityDetailModal";
import { Badge } from "../components/ui/Badge";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { PageHeader } from "../components/ui/PageHeader";
import { TruncatedText } from "../components/ui/TruncatedText";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { useServerDataTableRowSelection } from "../hooks/useServerDataTableRowSelection";
import {
  activityLabels,
  activityStatusLabels,
  activityStatusOptions,
  activityTypeLabels,
  activityTypeOptions,
  formatActivityDateShort,
} from "../labels/activityLabels";
import { labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import type { Activity, ActivityStatus, ActivityType } from "../types/activity";
import type { Customer } from "../types/customer";
import {
  activityStatusBadgeVariant,
  activityTypeBadgeVariant,
} from "../utils/badges";

interface ActivitiesPageProps {
  onOpenCustomer?: (customerId: string) => void;
}

type ConfirmState =
  | { type: "single"; activity: Activity }
  | { type: "bulk"; count: number }
  | null;

export function ActivitiesPage({ onOpenCustomer }: ActivitiesPageProps) {
  const [customers, setCustomers] = React.useState<Customer[]>([]);
  const [detail, setDetail] = React.useState<Activity | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmState>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [bulkDeleting, setBulkDeleting] = React.useState(false);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const table = useServerDataTable<Activity>({
    fetchFn: (params) =>
      listActivities({
        ...params,
        activityType: (params.filters.activityType as ActivityType | undefined) || undefined,
        status: params.filters.status || undefined,
        customerId: params.filters.customerId || undefined,
        dateFrom: params.filters.dateFrom || undefined,
        dateTo: params.filters.dateTo || undefined,
      }),
    defaultSort: { field: "activity_date", direction: "desc" },
    filterKeys: ["activityType", "status", "customerId", "dateFrom", "dateTo"],
    urlSync: true,
    urlPath: "/activities",
  });

  const pageRowIds = React.useMemo(() => table.items.map((item) => item.id), [table.items]);
  const rowSelection = useServerDataTableRowSelection(pageRowIds);
  const selectedCount = rowSelection.selectedIds.size;

  React.useEffect(() => {
    let cancelled = false;
    void listCustomers({ page: 1, pageSize: 100, sortBy: "display_name", sortOrder: "asc" })
      .then((result) => {
        if (!cancelled) setCustomers(result.items);
      })
      .catch(() => {
        if (!cancelled) setCustomers([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  const handleDeleteSingle = async (activity: Activity) => {
    setDeletingId(activity.id);
    setActionError(null);
    try {
      await deleteActivity(activity.id);
      setConfirm(null);
      if (detail?.id === activity.id) setDetail(null);
      rowSelection.clearSelection();
      setSuccess(activityLabels.deleteSuccess);
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : activityLabels.deleteError);
    } finally {
      setDeletingId(null);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedCount === 0) return;
    setBulkDeleting(true);
    setActionError(null);
    try {
      const result = await bulkDeleteActivities(Array.from(rowSelection.selectedIds));
      setConfirm(null);
      rowSelection.clearSelection();
      if (detail && result.deleted_ids.includes(detail.id)) setDetail(null);
      setSuccess(
        activityLabels.bulkDeleteSuccess(result.deleted_count, result.not_found_count),
      );
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : activityLabels.bulkDeleteError);
    } finally {
      setBulkDeleting(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<Activity>[]>(
    () => [
      {
        key: "customer_name",
        title: activityLabels.customer,
        sortField: "customer_name",
        allowWrap: true,
        render: (activity) =>
          onOpenCustomer ? (
            <button
              type="button"
              className="link-button"
              onClick={() => onOpenCustomer(activity.customer_id)}
              aria-label={activityLabels.openCustomer}
            >
              {activity.customer_name ?? "—"}
            </button>
          ) : (
            <span>{activity.customer_name ?? "—"}</span>
          ),
      },
      {
        key: "subject",
        title: activityLabels.subject,
        sortField: "subject",
        allowWrap: true,
        render: (activity) => (
          <button
            type="button"
            className="link-button"
            onClick={() => setDetail(activity)}
          >
            <TruncatedText value={activity.subject} maxLength={80} />
          </button>
        ),
      },
      {
        key: "actions",
        title: activityLabels.actions,
        sortable: false,
        className: "actions",
        render: (activity) => (
          <div className="table-actions">
            <button type="button" className="btn link" onClick={() => setDetail(activity)}>
              {activityLabels.view}
            </button>
            <button
              type="button"
              className="btn link danger"
              disabled={deletingId === activity.id}
              onClick={() => setConfirm({ type: "single", activity })}
            >
              {deletingId === activity.id ? labels.loading : activityLabels.delete}
            </button>
          </div>
        ),
      },
      {
        key: "activity_type",
        title: activityLabels.type,
        sortField: "activity_type",
        render: (activity) => (
          <Badge variant={activityTypeBadgeVariant(activity.type)}>
            {activity.related_outcome_name
              ? activity.related_outcome_name
              : (activityTypeLabels[activity.type] ?? activity.type)}
          </Badge>
        ),
      },
      {
        key: "activity_date",
        title: activityLabels.activityDate,
        sortField: "activity_date",
        render: (activity) => (
          <time dateTime={activity.activity_date}>
            {formatActivityDateShort(activity.activity_date)}
          </time>
        ),
      },
      {
        key: "status",
        title: activityLabels.status,
        sortField: "status",
        render: (activity) => (
          <Badge variant={activityStatusBadgeVariant(activity.status)}>
            {activityStatusLabels[activity.status] ?? activity.status}
          </Badge>
        ),
      },
      {
        key: "related_todo",
        title: activityLabels.relatedTodo,
        sortable: false,
        render: (activity) => activity.related_todo_title ?? "—",
      },
      {
        key: "follow_up_date",
        title: activityLabels.followUpDate,
        sortField: "follow_up_date",
        render: (activity) =>
          activity.follow_up_date ? formatActivityDateShort(activity.follow_up_date) : "—",
      },
    ],
    [deletingId, onOpenCustomer],
  );

  return (
    <div className="page activities-page">
      <PageHeader
        title={activityLabels.pageTitle}
        subtitle={`${table.pagination.totalItems} kayıt`}
        actions={
          selectedCount > 0 ? (
            <button
              type="button"
              className="btn danger"
              onClick={() => setConfirm({ type: "bulk", count: selectedCount })}
            >
              {activityLabels.deleteSelected} ({selectedCount})
            </button>
          ) : undefined
        }
      />

      {success ? <div className="banner success">{success}</div> : null}
      {actionError ? <div className="banner error">{actionError}</div> : null}
      {table.error ? <div className="banner error">{table.error}</div> : null}

      <UniversalDataTable
        table={table}
        columns={columns}
        rowKey={(activity) => activity.id}
        rowSelection={{
          controller: rowSelection,
          title: activityLabels.selectionColumn,
          selectAllAriaLabel: activityLabels.selectAllOnPage,
          rowAriaLabel: (activity) => activityLabels.selectRow(activity.subject),
        }}
        toolbar={
          <FilterPanel
            className="activity-filters"
            actions={
              <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
                Yenile
              </button>
            }
          >
            <input
              type="search"
              className="search-input"
              placeholder={activityLabels.searchPlaceholder}
              value={table.search}
              onChange={(event) => table.setSearch(event.target.value)}
              aria-label={activityLabels.searchPlaceholder}
            />
            <select
              value={table.filters.customerId ?? ""}
              onChange={(event) => table.setFilter("customerId", event.target.value)}
              aria-label={activityLabels.filterCustomer}
            >
              <option value="">{activityLabels.filterAll}</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.display_name}
                </option>
              ))}
            </select>
            <select
              value={table.filters.activityType ?? ""}
              onChange={(event) => table.setFilter("activityType", event.target.value)}
              aria-label={activityLabels.filterType}
            >
              <option value="">{activityLabels.filterAll}</option>
              {activityTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {activityTypeLabels[type]}
                </option>
              ))}
            </select>
            <select
              value={table.filters.status ?? ""}
              onChange={(event) => table.setFilter("status", event.target.value)}
              aria-label={activityLabels.filterStatus}
            >
              <option value="">{activityLabels.filterAll}</option>
              {activityStatusOptions.map((status: ActivityStatus) => (
                <option key={status} value={status}>
                  {activityStatusLabels[status]}
                </option>
              ))}
            </select>
            <input
              type="date"
              className="input"
              value={table.filters.dateFrom ?? ""}
              onChange={(event) => table.setFilter("dateFrom", event.target.value)}
              aria-label={activityLabels.filterDateFrom}
            />
            <input
              type="date"
              className="input"
              value={table.filters.dateTo ?? ""}
              onChange={(event) => table.setFilter("dateTo", event.target.value)}
              aria-label={activityLabels.filterDateTo}
            />
          </FilterPanel>
        }
        emptyState={
          <EmptyState
            title={
              table.search || Object.values(table.filters).some(Boolean)
                ? uiLabels.emptySearchTitle
                : activityLabels.emptyTitle
            }
            description={
              table.search || Object.values(table.filters).some(Boolean)
                ? uiLabels.emptySearchDescription
                : activityLabels.emptyDescription
            }
          />
        }
      />

      <ActivityDetailModal
        activity={detail}
        onClose={() => setDetail(null)}
        onOpenCustomer={onOpenCustomer}
      />

      {confirm?.type === "single" ? (
        <ConfirmDialog
          title={uiLabels.deleteActivityTitle}
          message={activityLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingId === confirm.activity.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleDeleteSingle(confirm.activity)}
        />
      ) : null}

      {confirm?.type === "bulk" ? (
        <ConfirmDialog
          title={activityLabels.bulkDeleteTitle}
          message={activityLabels.bulkDeleteConfirm(confirm.count)}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={bulkDeleting}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleBulkDelete()}
        />
      ) : null}
    </div>
  );
}
