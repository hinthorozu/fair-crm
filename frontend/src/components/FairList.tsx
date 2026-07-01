import React from "react";
import type { Fair, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { DataTableShell, SortableHeader } from "./ui/DataTable";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";

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
    <div className="filters">
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
      <button type="button" className="btn secondary" onClick={onRefresh}>
        {labels.refresh}
      </button>
    </div>
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

export function FairTable({
  items,
  onEdit,
  onArchive,
  onRestore,
  onOpenDetail,
  onCreate,
  archivingId,
  restoringId,
  sortField,
  sortDirection,
  onSortChange,
  emptyDueToFilters,
}: FairTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={emptyDueToFilters ? uiLabels.emptySearchTitle : fairLabels.noResults}
        description={emptyDueToFilters ? uiLabels.emptySearchDescription : undefined}
        actionLabel={onCreate ? uiLabels.createNew : undefined}
        onAction={onCreate}
      />
    );
  }

  return (
    <DataTableShell>
      <thead>
        <tr>
          <th>
            {onSortChange ? (
              <SortableHeader
                label={fairLabels.name}
                field="name"
                activeField={sortField ?? null}
                direction={sortDirection ?? null}
                onSort={onSortChange}
              />
            ) : (
              fairLabels.name
            )}
          </th>
          <th>{fairLabels.organizer}</th>
          <th>{fairLabels.venue}</th>
          <th>{labels.city}</th>
          <th>
            {onSortChange ? (
              <SortableHeader
                label={fairLabels.start_date}
                field="start_date"
                activeField={sortField ?? null}
                direction={sortDirection ?? null}
                onSort={onSortChange}
              />
            ) : (
              fairLabels.start_date
            )}
          </th>
          <th>{labels.status}</th>
          <th>{labels.actions}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((f) => {
          const isArchived = isArchivedFair(f);
          return (
            <tr key={f.id} className={isArchived ? "row-archived" : undefined}>
              <td>
                {onOpenDetail ? (
                  <button
                    type="button"
                    className="btn link table-link"
                    onClick={() => onOpenDetail(f.id)}
                  >
                    <strong>{f.name}</strong>
                  </button>
                ) : (
                  <strong>{f.name}</strong>
                )}
                {f.country && <div className="muted">{f.country}</div>}
              </td>
              <td>{f.organizer ?? "—"}</td>
              <td>{f.venue ?? "—"}</td>
              <td>{f.city ?? "—"}</td>
              <td>{formatDate(f.start_date)}</td>
              <td>
                <Badge variant={fairStatusVariant(f.status)}>
                  {fairStatusLabels[f.status] ?? f.status}
                </Badge>
              </td>
              <td className="actions">
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
              </td>
            </tr>
          );
        })}
      </tbody>
    </DataTableShell>
  );
}

export { Modal } from "./ui/Modal";
