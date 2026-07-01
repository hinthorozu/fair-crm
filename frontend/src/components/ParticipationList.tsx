import React from "react";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
} from "../types/participation";
import { participationLabels, participationStatusLabels } from "../labels/participationLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { DataTableShell } from "./ui/DataTable";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { participationStatusBadgeVariant } from "../utils/badges";

function formatFairDates(start: string | null, end: string | null): string {
  if (!start && !end) return "—";
  if (start && end) return `${start} – ${end}`;
  return start ?? end ?? "—";
}

function formatVisitedAt(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("tr-TR");
}

interface CustomerParticipationTableProps {
  items: CustomerParticipationListItem[];
  deletingId: string | null;
  onCreate?: () => void;
  onEdit: (item: CustomerParticipationListItem) => void;
  onDelete: (item: CustomerParticipationListItem) => void;
  emptyDueToFilters?: boolean;
}

export function CustomerParticipationTable({
  items,
  deletingId,
  onCreate,
  onEdit,
  onDelete,
  emptyDueToFilters,
}: CustomerParticipationTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={emptyDueToFilters ? uiLabels.emptySearchTitle : "Henüz fuar katılımı yok."}
        description={
          emptyDueToFilters ? uiLabels.emptySearchDescription : "Bu müşteriyi bir fuara ekleyerek başlayın."
        }
        actionLabel={onCreate ? participationLabels.addToFair : undefined}
        onAction={onCreate}
      />
    );
  }

  return (
    <DataTableShell>
      <thead>
        <tr>
          <th>{participationLabels.fair}</th>
          <th>{participationLabels.date}</th>
          <th>{participationLabels.hall}</th>
          <th>{participationLabels.stand}</th>
          <th>{participationLabels.status}</th>
          <th>{participationLabels.primaryContact}</th>
          <th>{participationLabels.visitedAt}</th>
          <th>{participationLabels.actions}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>
              <strong>{item.fair_name}</strong>
            </td>
            <td>{formatFairDates(item.fair_start_date, item.fair_end_date)}</td>
            <td>{item.hall ?? "—"}</td>
            <td>{item.stand ?? "—"}</td>
            <td>
              <Badge variant={participationStatusBadgeVariant(item.participation_status)}>
                {participationStatusLabels[item.participation_status]}
              </Badge>
            </td>
            <td>{item.primary_contact_name ?? "—"}</td>
            <td>{formatVisitedAt(item.visited_at)}</td>
            <td className="actions">
              <button type="button" className="btn link" onClick={() => onEdit(item)}>
                {participationLabels.edit}
              </button>
              <button
                type="button"
                className="btn link danger"
                disabled={deletingId === item.id}
                onClick={() => onDelete(item)}
              >
                {deletingId === item.id ? labels.loading : participationLabels.delete}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </DataTableShell>
  );
}

interface FairParticipantTableProps {
  items: FairParticipantListItem[];
  deletingId: string | null;
  onCreate?: () => void;
  onEdit: (item: FairParticipantListItem) => void;
  onDelete: (item: FairParticipantListItem) => void;
  onOpenCustomer?: (customerId: string) => void;
  emptyDueToFilters?: boolean;
}

export function FairParticipantTable({
  items,
  deletingId,
  onCreate,
  onEdit,
  onDelete,
  onOpenCustomer,
  emptyDueToFilters,
}: FairParticipantTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={emptyDueToFilters ? uiLabels.emptySearchTitle : "Henüz katılımcı firma yok."}
        description={
          emptyDueToFilters ? uiLabels.emptySearchDescription : "Bu fuara firma ekleyerek başlayın."
        }
        actionLabel={onCreate ? participationLabels.addCompany : undefined}
        onAction={onCreate}
      />
    );
  }

  return (
    <DataTableShell>
      <thead>
        <tr>
          <th>{participationLabels.company}</th>
          <th>{labels.email}</th>
          <th>{labels.phone}</th>
          <th>{labels.country}</th>
          <th>{labels.city}</th>
          <th>{participationLabels.hall}</th>
          <th>{participationLabels.stand}</th>
          <th>{participationLabels.status}</th>
          <th>{participationLabels.primaryContact}</th>
          <th>{participationLabels.actions}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>
              {onOpenCustomer ? (
                <button
                  type="button"
                  className="btn link table-link"
                  onClick={() => onOpenCustomer(item.customer_id)}
                >
                  <strong>{item.company_name}</strong>
                </button>
              ) : (
                <strong>{item.company_name}</strong>
              )}
            </td>
            <td>{item.email ?? "—"}</td>
            <td>{item.phone ?? "—"}</td>
            <td>{item.country ?? "—"}</td>
            <td>{item.city ?? "—"}</td>
            <td>{item.hall ?? "—"}</td>
            <td>{item.stand ?? "—"}</td>
            <td>
              <Badge variant={participationStatusBadgeVariant(item.participation_status)}>
                {participationStatusLabels[item.participation_status]}
              </Badge>
            </td>
            <td>{item.primary_contact_name ?? "—"}</td>
            <td className="actions">
              <button type="button" className="btn link" onClick={() => onEdit(item)}>
                {participationLabels.edit}
              </button>
              <button
                type="button"
                className="btn link danger"
                disabled={deletingId === item.id}
                onClick={() => onDelete(item)}
              >
                {deletingId === item.id ? labels.loading : participationLabels.delete}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </DataTableShell>
  );
}
