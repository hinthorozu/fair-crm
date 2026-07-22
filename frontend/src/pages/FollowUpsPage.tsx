import React from "react";
import {
  getTodoWorklistModalContext,
  recordTodoWorklistActivity,
} from "../api/todoWorklist";
import { listFollowUps } from "../api/followUps";
import { ApiError } from "../api/client";
import { TodoWorklistActivityModal } from "../components/todos/TodoWorklistActivityModal";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { FilterPanel } from "../components/ui/FilterPanel";
import { TextInput } from "../components/ui/form";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { followUpLabels, followUpFilterOptions } from "../labels/followUpLabels";
import { labels } from "../labels";
import { todoWorklistLabels, worklistStatusBadgeVariant, worklistStatusLabels } from "../labels/todoWorklistLabels";
import type { FollowUpFilter, FollowUpRow } from "../types/followUps";
import { Banner } from "../components/ui/Banner";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { PageShell } from "../components/ui/PageShell";
import type {
  RecordTodoWorklistActivityPayload,
  TodoWorklistModalContext,
} from "../types/todoWorklist";

interface FollowUpsPageProps {
  onOpenCustomer?: (customerId: string) => void;
  embedded?: boolean;
  lockedFilter?: FollowUpFilter;
  urlPath?: string;
  hidePageChrome?: boolean;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR");
}

function followUpRowKey(row: Pick<FollowUpRow, "todo_id" | "customer_id">): string {
  return `${row.todo_id}:${row.customer_id}`;
}

export function FollowUpsPage({
  onOpenCustomer,
  embedded = false,
  lockedFilter,
  urlPath = "/follow-ups",
  hidePageChrome = false,
}: FollowUpsPageProps) {
  const [activityModalOpen, setActivityModalOpen] = React.useState(false);
  const [selectedTodoId, setSelectedTodoId] = React.useState<string | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = React.useState<string | null>(null);
  const [modalContext, setModalContext] = React.useState<TodoWorklistModalContext | null>(null);
  const [modalLoading, setModalLoading] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState<string | null>(null);

  const defaultFilter: FollowUpFilter = lockedFilter ?? "bugun";

  const table = useServerDataTable<FollowUpRow>({
    fetchFn: (params) =>
      listFollowUps({
        page: params.page,
        pageSize: params.pageSize,
        search: params.search,
        sortBy: params.sortBy ?? undefined,
        sortOrder: params.sortOrder ?? undefined,
        filter: lockedFilter ?? (params.filters.filter as FollowUpFilter | undefined) ?? "bugun",
      }),
    defaultSort: { field: "follow_up_at", direction: "asc" },
    defaultFilters: { filter: defaultFilter },
    filterKeys: ["filter"],
    urlSync: !lockedFilter,
    urlPath,
  });

  const followUpFilter =
    lockedFilter ?? (table.filters.filter as FollowUpFilter | undefined) ?? "bugun";

  const loadModalContext = React.useCallback(async (todoId: string, customerId: string) => {
    setModalLoading(true);
    setSaveError(null);
    try {
      const context = await getTodoWorklistModalContext(todoId, customerId);
      setModalContext(context);
    } catch (err) {
      setModalContext(null);
      setSaveError(err instanceof ApiError ? err.message : followUpLabels.loadError);
    } finally {
      setModalLoading(false);
    }
  }, []);

  const closeActivityModal = React.useCallback(() => {
    setActivityModalOpen(false);
    setSelectedTodoId(null);
    setSelectedCustomerId(null);
    setModalContext(null);
    setSaveError(null);
  }, []);

  const handleOpenActivity = (row: FollowUpRow) => {
    setSelectedTodoId(row.todo_id);
    setSelectedCustomerId(row.customer_id);
    setActivityModalOpen(true);
    setSaveSuccess(null);
    setSaveError(null);
    void loadModalContext(row.todo_id, row.customer_id);
  };

  const resolveNextRow = (
    items: FollowUpRow[],
    currentKey: string,
    currentIndex: number,
  ): FollowUpRow | null => {
    if (items.length === 0) return null;
    const sameIndex = items[currentIndex];
    if (sameIndex && followUpRowKey(sameIndex) !== currentKey) {
      return sameIndex;
    }
    return items[currentIndex + 1] ?? null;
  };

  const handleSaveActivity = async (payload: RecordTodoWorklistActivityPayload) => {
    if (!selectedTodoId || !selectedCustomerId) return;
    const currentKey = followUpRowKey({
      todo_id: selectedTodoId,
      customer_id: selectedCustomerId,
    });
    const currentIndex = table.items.findIndex((row) => followUpRowKey(row) === currentKey);
    const advance = payload.advance_to_next;

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      await recordTodoWorklistActivity(selectedTodoId, selectedCustomerId, {
        ...payload,
        advance_to_next: false,
      });
      setSaveSuccess(todoWorklistLabels.saveSuccess);
      await table.refresh();

      if (advance) {
        const fresh = await listFollowUps({
          page: table.pagination.page,
          pageSize: table.pagination.pageSize,
          search: table.search,
          sortBy: table.sorting.field || undefined,
          sortOrder: table.sorting.direction || undefined,
          filter: followUpFilter,
        });
        const nextRow = resolveNextRow(fresh.items, currentKey, currentIndex);
        if (nextRow) {
          setSelectedTodoId(nextRow.todo_id);
          setSelectedCustomerId(nextRow.customer_id);
          await loadModalContext(nextRow.todo_id, nextRow.customer_id);
        } else {
          closeActivityModal();
        }
      } else {
        closeActivityModal();
      }
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : followUpLabels.saveError);
    } finally {
      setSaving(false);
    }
  };

  const handleFilterChange = (filter: FollowUpFilter) => {
    if (lockedFilter) return;
    table.setFilter("filter", filter);
  };

  const columns = React.useMemo<UniversalDataTableColumn<FollowUpRow>[]>(
    () => [
      {
        key: "customer_name",
        title: followUpLabels.colCustomer,
        sortField: "company_name",
        render: (row) => (
          <TableEntityLink onClick={() => handleOpenActivity(row)}>
            {row.customer_name}
          </TableEntityLink>
        ),
      },
      {
        key: "location",
        title: followUpLabels.colCityCountry,
        render: (row) => [row.city, row.country].filter(Boolean).join(" / ") || "—",
      },
      {
        key: "phone_summary",
        title: followUpLabels.colPhone,
        priority: "secondary",
        render: (row) => <span className="text-wrap">{row.phone_summary || "—"}</span>,
      },
      {
        key: "email_summary",
        title: followUpLabels.colEmail,
        priority: "secondary",
        render: (row) => <span className="text-wrap">{row.email_summary || "—"}</span>,
      },
      {
        key: "last_outcome_name",
        title: followUpLabels.colLastOutcome,
        priority: "secondary",
        render: (row) => row.last_outcome_name || "—",
      },
      {
        key: "last_note_summary",
        title: followUpLabels.colLastNote,
        priority: "secondary",
        render: (row) => <span className="text-truncate-2">{row.last_note_summary || "—"}</span>,
      },
      {
        key: "follow_up_at",
        title: followUpLabels.colFollowUp,
        sortField: "follow_up_at",
        render: (row) => formatDateTime(row.follow_up_at),
      },
      {
        key: "todo_title",
        title: followUpLabels.colSourceTask,
        sortField: "todo_title",
        priority: "secondary",
        render: (row) => row.todo_title,
      },
      {
        key: "primary_status",
        title: followUpLabels.colStatus,
        sortField: "primary_status",
        render: (row) => (
          <Badge variant={worklistStatusBadgeVariant(row.primary_status)}>
            {worklistStatusLabels[row.primary_status]}
          </Badge>
        ),
      },
      {
        key: "action_required",
        title: followUpLabels.colActionRequired,
        sortable: false,
        priority: "secondary",
        render: (row) =>
          row.action_required ? (
            <Badge variant="warning">{followUpLabels.flagYes}</Badge>
          ) : (
            followUpLabels.flagNo
          ),
      },
      {
        key: "data_problem",
        title: followUpLabels.colDataProblem,
        sortable: false,
        priority: "secondary",
        render: (row) =>
          row.data_problem ? (
            <Badge variant="warning">{followUpLabels.flagYes}</Badge>
          ) : (
            followUpLabels.flagNo
          ),
      },
      {
        key: "actions",
        title: followUpLabels.colActions,
        sortable: false,
        priority: "primary",
        className: "actions",
        render: (row) => (
          <button
            type="button"
            className="btn secondary small"
            onClick={() => onOpenCustomer?.(row.customer_id)}
          >
            {todoWorklistLabels.openCustomerCard}
          </button>
        ),
      },
    ],
    [onOpenCustomer],
  );

  const body = (
    <>
      <section className="follow-ups-section">
        <UniversalDataTable
          table={table}
          skeletonCols={12}
          toolbar={
            <FilterPanel
              actions={
                <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
                  {labels.refresh}
                </button>
              }
            >
              {!lockedFilter ? (
                <div className="field full-width todo-worklist-segments">
                  {followUpFilterOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`btn ${followUpFilter === option.value ? "primary" : "secondary"}`}
                      onClick={() => handleFilterChange(option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              ) : null}
              <TextInput
                id="follow-up-search"
                type="search"
                className="search-input"
                placeholder={followUpLabels.searchPlaceholder}
                value={table.search}
                onChange={(e) => table.setSearch(e.target.value)}
                aria-label={followUpLabels.searchPlaceholder}
              />
            </FilterPanel>
          }
          columns={columns}
          rowKey={(row) => followUpRowKey(row)}
          emptyState={<EmptyState title={followUpLabels.emptyList} />}
        />
      </section>

      {saveSuccess && <Banner variant="success">{saveSuccess}</Banner>}

      <TodoWorklistActivityModal
        open={activityModalOpen}
        context={modalContext}
        loading={modalLoading}
        saving={saving}
        error={saveError}
        onClose={closeActivityModal}
        onSave={handleSaveActivity}
      />
    </>
  );

  if (hidePageChrome || embedded) {
    return <div className="follow-ups-page follow-ups-page--embedded">{body}</div>;
  }

  return (
    <PageShell className="follow-ups-page">
      <PageHeader title={followUpLabels.pageTitle} />
      {body}
    </PageShell>
  );
}
