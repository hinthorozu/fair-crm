import React from "react";
import type { Fair, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import { FilterPanel } from "./ui/FilterPanel";

interface FairFiltersProps {
  search: string;
  status: FairStatus | "";
  onSearchChange: (value: string) => void;
  onStatusChange: (value: FairStatus | "") => void;
  onRefresh: () => void;
}

export function FairFilters({
  search,
  status,
  onSearchChange,
  onStatusChange,
  onRefresh,
}: FairFiltersProps) {
  return (
    <FilterPanel
      actions={
        <button type="button" className="btn secondary" onClick={onRefresh}>
          {labels.refresh}
        </button>
      }
    >
      <input
        type="search"
        className="search-input"
        placeholder={uiLabels.searchFair}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        aria-label={uiLabels.searchFair}
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as FairStatus | "")}
        aria-label={labels.status}
      >
        <option value="">{labels.allStatuses}</option>
        {(["planned", "active", "completed", "cancelled", "archived"] as FairStatus[]).map((s) => (
          <option key={s} value={s}>
            {fairStatusLabels[s]}
          </option>
        ))}
      </select>
    </FilterPanel>
  );
}

interface FairTableProps {
  items: Fair[];
  onEdit: (fair: Fair) => void;
  onArchive: (fair: Fair) => void;
  onRestore: (fair: Fair) => void;
  onOpenDetail?: (fairId: string) => void;
  onCreate?: () => void;
  archivingId: string | null;
  restoringId: string | null;
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
  emptyDueToFilters?: boolean;
}

function isArchivedFair(fair: Fair): boolean {
  return fair.status === "archived" || fair.deleted_at !== null;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return value;
}

function fairStatusVariant(status: FairStatus): "warning" | "success" | "neutral" | "danger" | "info" {
  const map: Record<string, "warning" | "success" | "neutral" | "danger" | "info"> = {
    planned: "info",
    active: "success",
    completed: "neutral",
    cancelled: "danger",
    archived: "danger",
  };
  return map[status] ?? "neutral";
}

function buildFairColumns(props: FairTableProps): UniversalDataTableColumn<Fair>[] {
  const { onEdit, onArchive, onRestore, onOpenDetail, archivingId, restoringId } = props;
  return [
    {
      key: "name",
      title: fairLabels.name,
      sortable: true,
      render: (f) => (
        <>
          {onOpenDetail ? (
            <button type="button" className="btn link table-link" onClick={() => onOpenDetail(f.id)}>
              <strong>{f.name}</strong>
            </button>
          ) : (
            <strong>{f.name}</strong>
          )}
          {f.country && <div className="muted">{f.country}</div>}
        </>
      ),
    },
    {
      key: "organizer",
      title: fairLabels.organizer,
      sortable: true,
      priority: "secondary",
      render: (f) => f.organizer ?? "—",
    },
    {
      key: "venue",
      title: fairLabels.venue,
      sortable: true,
      priority: "secondary",
      render: (f) => f.venue ?? "—",
    },
    {
      key: "city",
      title: labels.city,
      sortable: true,
      render: (f) => f.city ?? "—",
    },
    {
      key: "start_date",
      title: fairLabels.start_date,
      sortable: true,
      render: (f) => formatDate(f.start_date),
    },
    {
      key: "status",
      title: labels.status,
      sortable: true,
      render: (f) => (
        <Badge variant={fairStatusVariant(f.status)}>
          {fairStatusLabels[f.status] ?? f.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      title: labels.actions,
      sortable: false,
      priority: "primary",
      className: "actions",
      render: (f) => {
        const isArchived = isArchivedFair(f);
        return (
          <>
            {isArchived && (
              <button
                type="button"
                className="btn link"
                disabled={restoringId === f.id}
                onClick={() => onRestore(f)}
              >
                {restoringId === f.id ? labels.loading : labels.restore}
              </button>
            )}
            {!isArchived && (
              <>
                <button type="button" className="btn link" onClick={() => onEdit(f)}>
                  {labels.edit}
                </button>
                <button
                  type="button"
                  className="btn link danger"
                  disabled={archivingId === f.id}
                  onClick={() => onArchive(f)}
                >
                  {archivingId === f.id ? labels.loading : labels.archive}
                </button>
              </>
            )}
          </>
        );
      },
    },
  ];
}

export function FairTable(props: FairTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildFairColumns(props)}
      items={items}
      rowKey={(f) => f.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : fairLabels.noResults}
          description={emptyDueToFilters ? uiLabels.emptySearchDescription : undefined}
          actionLabel={onCreate ? uiLabels.createNew : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}

export { Modal } from "./ui/Modal";
