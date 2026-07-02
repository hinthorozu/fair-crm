import React from "react";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import { customerStatusBadgeVariant } from "../utils/badges";

interface CustomerFiltersProps {
  search: string;
  status: CustomerStatus | "";
  customerType: CustomerType | "";
  onSearchChange: (value: string) => void;
  onStatusChange: (value: CustomerStatus | "") => void;
  onTypeChange: (value: CustomerType | "") => void;
  onRefresh: () => void;
}

export function CustomerFilters({
  search,
  status,
  customerType,
  onSearchChange,
  onStatusChange,
  onTypeChange,
  onRefresh,
}: CustomerFiltersProps) {
  return (
    <div className="filters">
      <input
        type="search"
        className="search-input"
        placeholder={uiLabels.searchCustomer}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        aria-label={uiLabels.searchCustomer}
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as CustomerStatus | "")}
        aria-label={labels.status}
      >
        <option value="">{labels.allStatuses}</option>
        {(["lead", "active", "inactive", "archived"] as CustomerStatus[]).map((s) => (
          <option key={s} value={s}>
            {customerStatusLabels[s]}
          </option>
        ))}
      </select>
      <select
        value={customerType}
        onChange={(e) => onTypeChange(e.target.value as CustomerType | "")}
        aria-label={labels.customer_type}
      >
        <option value="">{labels.allTypes}</option>
        {Object.entries(customerTypeLabels).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <button type="button" className="btn secondary" onClick={onRefresh}>
        {labels.refresh}
      </button>
    </div>
  );
}

interface CustomerTableProps {
  items: Customer[];
  onEdit: (customer: Customer) => void;
  onArchive: (customer: Customer) => void;
  onRestore: (customer: Customer) => void;
  onOpenDetail?: (customer: Customer) => void;
  onCreate?: () => void;
  archivingId: string | null;
  restoringId: string | null;
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
  emptyDueToFilters?: boolean;
}

function isArchivedCustomer(customer: Customer): boolean {
  return customer.status === "archived" || customer.deleted_at !== null;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildCustomerColumns(props: CustomerTableProps): UniversalDataTableColumn<Customer>[] {
  const { onEdit, onArchive, onRestore, onOpenDetail, archivingId, restoringId } = props;
  return [
    {
      key: "name",
      title: labels.display_name,
      sortable: true,
      render: (c) => (
        <>
          {onOpenDetail ? (
            <button type="button" className="btn link name-link" onClick={() => onOpenDetail(c)}>
              <strong>{c.display_name}</strong>
            </button>
          ) : (
            <strong>{c.display_name}</strong>
          )}
          {c.trade_name && <div className="muted">{c.trade_name}</div>}
        </>
      ),
    },
    {
      key: "city",
      title: labels.city,
      sortable: true,
      render: (c) => c.city ?? "—",
    },
    {
      key: "customer_type",
      title: labels.customer_type,
      sortable: true,
      render: (c) => customerTypeLabels[c.customer_type] ?? c.customer_type,
    },
    {
      key: "status",
      title: labels.status,
      sortable: true,
      render: (c) => (
        <Badge variant={customerStatusBadgeVariant(c.status)}>
          {customerStatusLabels[c.status] ?? c.status}
        </Badge>
      ),
    },
    {
      key: "phone",
      title: labels.phone,
      sortable: true,
      render: (c) => c.phone ?? "—",
    },
    {
      key: "created_at",
      title: labels.created_at,
      sortable: true,
      render: (c) => formatDateTime(c.created_at),
    },
    {
      key: "updated_at",
      title: labels.updated_at,
      sortable: true,
      render: (c) => formatDateTime(c.updated_at),
    },
    {
      key: "actions",
      title: labels.actions,
      sortable: false,
      className: "actions",
      render: (c) => {
        const isArchived = isArchivedCustomer(c);
        return (
          <>
            {isArchived && (
              <button
                type="button"
                className="btn link"
                disabled={restoringId === c.id}
                onClick={() => onRestore(c)}
              >
                {restoringId === c.id ? labels.loading : labels.restore}
              </button>
            )}
            {!isArchived && (
              <>
                <button type="button" className="btn link" onClick={() => onEdit(c)}>
                  {labels.edit}
                </button>
                <button
                  type="button"
                  className="btn link danger"
                  disabled={archivingId === c.id}
                  onClick={() => onArchive(c)}
                >
                  {archivingId === c.id ? labels.loading : labels.archive}
                </button>
              </>
            )}
          </>
        );
      },
    },
  ];
}

export function CustomerTable(props: CustomerTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildCustomerColumns(props)}
      items={items}
      rowKey={(c) => c.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : uiLabels.emptyCustomersTitle}
          description={
            emptyDueToFilters
              ? uiLabels.emptySearchDescription
              : uiLabels.emptyCustomersDescription
          }
          actionLabel={onCreate ? uiLabels.createNew : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}

export { Modal } from "./ui/Modal";
