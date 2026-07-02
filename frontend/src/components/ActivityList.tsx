import React from "react";
import type { Activity } from "../types/activity";
import {
  activityLabels,
  activitySourceLabels,
  activityStatusLabels,
  activityTypeLabels,
  formatActivityDate,
  formatActivityDateShort,
} from "../labels/activityLabels";
import { labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import {
  activitySourceBadgeVariant,
  activityStatusBadgeVariant,
  activityTypeBadgeVariant,
} from "../utils/badges";

interface ActivityTableProps {
  items: Activity[];
  deletingId: string | null;
  onEdit: (activity: Activity) => void;
  onDelete: (activity: Activity) => void;
  onCreate?: () => void;
  emptyDueToFilters?: boolean;
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
}

function buildActivityColumns(props: ActivityTableProps): UniversalDataTableColumn<Activity>[] {
  const { onEdit, onDelete, deletingId } = props;
  return [
    {
      key: "activity_date",
      title: activityLabels.activityDate,
      sortable: true,
      render: (a) => (
        <time dateTime={a.activity_date}>{formatActivityDateShort(a.activity_date)}</time>
      ),
    },
    {
      key: "activity_type",
      title: activityLabels.type,
      sortable: true,
      render: (a) => (
        <Badge variant={activityTypeBadgeVariant(a.type)}>
          {activityTypeLabels[a.type] ?? a.type}
        </Badge>
      ),
    },
    {
      key: "status",
      title: activityLabels.status,
      sortable: true,
      render: (a) => (
        <Badge variant={activityStatusBadgeVariant(a.status)}>
          {activityStatusLabels[a.status] ?? a.status}
        </Badge>
      ),
    },
    {
      key: "subject",
      title: activityLabels.subject,
      sortable: true,
      render: (a) => (
        <>
          <strong>{a.subject}</strong>
          {a.description && <div className="muted">{a.description}</div>}
        </>
      ),
    },
    {
      key: "follow_up_date",
      title: activityLabels.followUpDate,
      sortable: true,
      render: (a) => (a.follow_up_date ? formatActivityDate(a.follow_up_date) : "—"),
    },
    {
      key: "contact",
      title: activityLabels.contact,
      sortable: false,
      render: (a) => a.contact_full_name ?? "—",
    },
    {
      key: "source",
      title: activityLabels.source,
      sortable: false,
      render: (a) => (
        <Badge variant={activitySourceBadgeVariant(a.source)}>
          {activitySourceLabels[a.source] ?? a.source}
        </Badge>
      ),
    },
    {
      key: "actions",
      title: activityLabels.actions,
      sortable: false,
      className: "actions",
      render: (a) => (
        <>
          <button type="button" className="btn link" onClick={() => onEdit(a)}>
            {activityLabels.edit}
          </button>
          <button
            type="button"
            className="btn link danger"
            disabled={deletingId === a.id}
            onClick={() => onDelete(a)}
          >
            {deletingId === a.id ? labels.loading : activityLabels.delete}
          </button>
        </>
      ),
    },
  ];
}

export function ActivityTable(props: ActivityTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildActivityColumns(props)}
      items={items}
      rowKey={(a) => a.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : uiLabels.emptyActivitiesTitle}
          description={
            emptyDueToFilters ? uiLabels.emptySearchDescription : uiLabels.emptyActivitiesDescription
          }
          actionLabel={onCreate ? uiLabels.createNew : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}

/** @deprecated Use ActivityTable — timeline replaced by Universal DataTable standard */
export { ActivityTable as ActivityTimeline };
