import React from "react";
import type {
  CustomerParticipationListItem,
  FairParticipantListItem,
} from "../types/participation";
import { participationLabels } from "../labels/participationLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import { TableRowActions } from "./ui/TableRowActions";
import { TableEntityLink } from "./ui/TableEntityLink";

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
      key: "notes",
      title: participationLabels.notes,
      sortable: true,
      render: (item) => item.notes ?? "—",
    },
    {
      key: "actions",
      title: participationLabels.actions,
      sortable: false,
      className: "actions",
      render: (item) => (
        <TableRowActions>
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
        </TableRowActions>
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
          <TableEntityLink onClick={() => onOpenCustomer(item.customer_id)}>
            {item.company_name}
          </TableEntityLink>
        ) : (
          <strong>{item.company_name}</strong>
        ),
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
      key: "notes",
      title: participationLabels.notes,
      sortable: true,
      render: (item) => item.notes ?? "—",
    },
    {
      key: "actions",
      title: participationLabels.actions,
      sortable: false,
      className: "actions",
      render: (item) => (
        <TableRowActions>
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
        </TableRowActions>
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
