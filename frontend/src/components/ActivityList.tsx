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
import { Card } from "./ui/Card";
import {
  activitySourceBadgeVariant,
  activityStatusBadgeVariant,
  activityTypeBadgeVariant,
} from "../utils/badges";

interface ActivityTimelineProps {
  items: Activity[];
  deletingId: string | null;
  onEdit: (activity: Activity) => void;
  onDelete: (activity: Activity) => void;
  onCreate?: () => void;
  emptyDueToFilters?: boolean;
}

export function ActivityTimeline({
  items,
  deletingId,
  onEdit,
  onDelete,
  onCreate,
  emptyDueToFilters,
}: ActivityTimelineProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={emptyDueToFilters ? uiLabels.emptySearchTitle : uiLabels.emptyActivitiesTitle}
        description={
          emptyDueToFilters ? uiLabels.emptySearchDescription : uiLabels.emptyActivitiesDescription
        }
        actionLabel={onCreate ? uiLabels.createNew : undefined}
        onAction={onCreate}
      />
    );
  }

  return (
    <div className="activity-timeline" role="list">
      {items.map((a) => (
        <article key={a.id} className="activity-timeline-item" role="listitem">
          <div className="activity-timeline-marker" aria-hidden="true">
            <span className="activity-timeline-dot" />
          </div>
          <Card className="activity-timeline-card">
            <div className="activity-timeline-header">
              <time className="activity-timeline-date" dateTime={a.activity_date}>
                {formatActivityDateShort(a.activity_date)}
              </time>
              <div className="activity-timeline-badges">
                <Badge variant={activityTypeBadgeVariant(a.type)}>
                  {activityTypeLabels[a.type] ?? a.type}
                </Badge>
                <Badge variant={activityStatusBadgeVariant(a.status)}>
                  {activityStatusLabels[a.status] ?? a.status}
                </Badge>
                <Badge variant={activitySourceBadgeVariant(a.source)}>
                  {activitySourceLabels[a.source] ?? a.source}
                </Badge>
              </div>
            </div>

            <h3 className="activity-timeline-subject">{a.subject}</h3>

            {a.description && (
              <p className="activity-timeline-description muted">{a.description}</p>
            )}

            <div className="activity-timeline-meta">
              {a.contact_full_name && (
                <span>
                  <strong>{activityLabels.contact}:</strong> {a.contact_full_name}
                </span>
              )}
              {a.follow_up_date && (
                <span className="activity-follow-up">
                  <strong>{activityLabels.followUpDate}:</strong>{" "}
                  {formatActivityDate(a.follow_up_date)}
                </span>
              )}
            </div>

            <div className="activity-timeline-actions">
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
            </div>
          </Card>
        </article>
      ))}
    </div>
  );
}

// Keep export name for backward compatibility
export { ActivityTimeline as ActivityTable };
