import type { Activity } from "../types/activity";
import {
  activityLabels,
  activitySourceLabels,
  activityStatusLabels,
  activityTypeLabels,
  formatActivityDate,
} from "../labels/activityLabels";
import { Modal } from "./ui/Modal";
import { Badge } from "./ui/Badge";
import { TableEntityLink } from "./ui/TableEntityLink";
import {
  activitySourceBadgeVariant,
  activityStatusBadgeVariant,
  activityTypeBadgeVariant,
} from "../utils/badges";

interface ActivityDetailModalProps {
  activity: Activity | null;
  onClose: () => void;
  onOpenCustomer?: (customerId: string) => void;
}

function boolLabel(value: boolean | null | undefined): string {
  if (value == null) return "—";
  return value ? activityLabels.yes : activityLabels.no;
}

function metadataLabel(key: string): string {
  switch (key) {
    case "source_detail":
      return activityLabels.source;
    case "delivery_status":
      return "Teslim durumu";
    case "recipient_email":
      return "Alıcı e-posta";
    default:
      return key;
  }
}

export function ActivityDetailModal({
  activity,
  onClose,
  onOpenCustomer,
}: ActivityDetailModalProps) {
  if (!activity) return null;

  const displayMeta = activity.display_metadata ?? {};
  const metaEntries = Object.entries(displayMeta).filter(
    ([, value]) => value != null && String(value).trim() !== "",
  );

  const customerName = activity.customer_name?.trim() || null;
  const customerId = activity.customer_id;
  const canOpenCustomer = Boolean(customerId && onOpenCustomer);
  const relatedTodoTitle = activity.related_todo_title?.trim() || null;

  return (
    <Modal title={activityLabels.detailTitle} onClose={onClose}>
      <div className="detail-grid compact">
        <div>
          <strong>{activityLabels.customer}</strong>
          <div>
            {canOpenCustomer && customerId && onOpenCustomer ? (
              <TableEntityLink onClick={() => onOpenCustomer(customerId)}>
                {customerName ?? "—"}
              </TableEntityLink>
            ) : (
              (customerName ?? "—")
            )}
          </div>
        </div>
        <div>
          <strong>{activityLabels.type}</strong>
          <div>
            <Badge variant={activityTypeBadgeVariant(activity.type)}>
              {activityTypeLabels[activity.type] ?? activity.type}
            </Badge>
          </div>
        </div>
        <div>
          <strong>{activityLabels.status}</strong>
          <div>
            <Badge variant={activityStatusBadgeVariant(activity.status)}>
              {activityStatusLabels[activity.status] ?? activity.status}
            </Badge>
          </div>
        </div>
        <div>
          <strong>{activityLabels.source}</strong>
          <div>
            <Badge variant={activitySourceBadgeVariant(activity.source)}>
              {activitySourceLabels[activity.source] ?? activity.source}
            </Badge>
          </div>
        </div>
        <div className="span-2">
          <strong>{activityLabels.subject}</strong>
          <div>{activity.subject}</div>
        </div>
        <div className="span-2">
          <strong>{activityLabels.description}</strong>
          <div>{activity.description?.trim() || "—"}</div>
        </div>
        <div>
          <strong>{activityLabels.activityDate}</strong>
          <div>{formatActivityDate(activity.activity_date)}</div>
        </div>
        <div>
          <strong>{activityLabels.followUpDate}</strong>
          <div>
            {activity.follow_up_date ? formatActivityDate(activity.follow_up_date) : "—"}
          </div>
        </div>
        <div>
          <strong>{activityLabels.createdAt}</strong>
          <div>{formatActivityDate(activity.created_at)}</div>
        </div>
        <div>
          <strong>{activityLabels.contact}</strong>
          <div>{activity.contact_full_name ?? "—"}</div>
        </div>
        <div>
          <strong>{activityLabels.relatedTodo}</strong>
          <div>{relatedTodoTitle ?? "—"}</div>
        </div>
        <div>
          <strong>{activityLabels.relatedOutcome}</strong>
          <div>{activity.related_outcome_name ?? "—"}</div>
        </div>
        <div>
          <strong>{activityLabels.actionRequired}</strong>
          <div>{boolLabel(activity.action_required)}</div>
        </div>
        <div>
          <strong>{activityLabels.dataProblem}</strong>
          <div>{boolLabel(activity.data_problem)}</div>
        </div>
        {metaEntries.map(([key, value]) => (
          <div key={key}>
            <strong>{metadataLabel(key)}</strong>
            <div>{String(value)}</div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
