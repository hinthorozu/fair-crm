import React from "react";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
} from "../types/participation";
import { participationLabels, participationStatusLabels } from "../labels/participationLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
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
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
}

function buildCustomerParticipationColumns(
  props: CustomerParticipationTableProps,
): UniversalDataTableColumn<CustomerParticipationListItem>[] {
  const { onEdit, onDelete, deletingId } = props;
  return [
    {
      key: "fair_name",
      title: participationLabels.fair,
      sortable: true,
      render: (item) => <strong>{item.fair_name}</strong>,
    },
    {
      key: "fair_start_date",
      title: participationLabels.date,
      sortable: true,
      render: (item) => formatFairDates(item.fair_start_date, item.fair_end_date),
    },
    {
      key: "hall",
      title: participationLabels.hall,
      sortable: true,
      render: (item) => item.hall ?? "—",
    },
    {
      key: "stand",
      title: participationLabels.stand,
      sortable: true,
      render: (item) => item.stand ?? "—",
    },
    {
      key: "participation_status",
      title: participationLabels.status,
      sortable: true,
      render: (item) => (
        <Badge variant={participationStatusBadgeVariant(item.participation_status)}>
          {participationStatusLabels[item.participation_status]}
        </Badge>
      ),
    },
    {
      key: "primary_contact_name",
      title: participationLabels.primaryContact,
      sortable: true,
      render: (item) => item.primary_contact_name ?? "—",
    },
    {
      key: "visited_at",
      title: participationLabels.visitedAt,
      sortable: true,
      render: (item) => formatVisitedAt(item.visited_at),
    },
    {
      key: "actions",
      title: participationLabels.actions,
      sortable: false,
      className: "actions",
      render: (item) => (
        <>
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
        </>
      ),
    },
  ];
}

export function CustomerParticipationTable(props: CustomerParticipationTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildCustomerParticipationColumns(props)}
      items={items}
      rowKey={(item) => item.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : "Henüz fuar katılımı yok."}
          description={
            emptyDueToFilters ? uiLabels.emptySearchDescription : "Bu müşteriyi bir fuara ekleyerek başlayın."
          }
          actionLabel={onCreate ? participationLabels.addToFair : undefined}
          onAction={onCreate}
        />
      }
    />
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
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
}

function buildFairParticipantColumns(
  props: FairParticipantTableProps,
): UniversalDataTableColumn<FairParticipantListItem>[] {
  const { onEdit, onDelete, onOpenCustomer, deletingId } = props;
  return [
    {
      key: "company_name",
      title: participationLabels.company,
      sortable: true,
      render: (item) =>
        onOpenCustomer ? (
          <button
            type="button"
            className="btn link table-link"
            onClick={() => onOpenCustomer(item.customer_id)}
          >
            <strong>{item.company_name}</strong>
          </button>
        ) : (
          <strong>{item.company_name}</strong>
        ),
    },
    {
      key: "email",
      title: labels.email,
      sortable: true,
      render: (item) => item.email ?? "—",
    },
    {
      key: "phone",
      title: labels.phone,
      sortable: true,
      render: (item) => item.phone ?? "—",
    },
    {
      key: "country",
      title: labels.country,
      sortable: true,
      render: (item) => item.country ?? "—",
    },
    {
      key: "city",
      title: labels.city,
      sortable: true,
      render: (item) => item.city ?? "—",
    },
    {
      key: "hall",
      title: participationLabels.hall,
      sortable: true,
      render: (item) => item.hall ?? "—",
    },
    {
      key: "stand",
      title: participationLabels.stand,
      sortable: true,
      render: (item) => item.stand ?? "—",
    },
    {
      key: "participation_status",
      title: participationLabels.status,
      sortable: true,
      render: (item) => (
        <Badge variant={participationStatusBadgeVariant(item.participation_status)}>
          {participationStatusLabels[item.participation_status]}
        </Badge>
      ),
    },
    {
      key: "primary_contact_name",
      title: participationLabels.primaryContact,
      sortable: true,
      render: (item) => item.primary_contact_name ?? "—",
    },
    {
      key: "actions",
      title: participationLabels.actions,
      sortable: false,
      className: "actions",
      render: (item) => (
        <>
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
        </>
      ),
    },
  ];
}

export function FairParticipantTable(props: FairParticipantTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildFairParticipantColumns(props)}
      items={items}
      rowKey={(item) => item.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : "Henüz katılımcı firma yok."}
          description={
            emptyDueToFilters ? uiLabels.emptySearchDescription : "Bu fuara firma ekleyerek başlayın."
          }
          actionLabel={onCreate ? participationLabels.addCompany : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}
