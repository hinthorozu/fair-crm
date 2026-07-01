import React from "react";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { Badge } from "./ui/Badge";
import { DataTable } from "./ui/DataTable";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
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
}

function isArchivedCustomer(customer: Customer): boolean {
  return customer.status === "archived" || customer.deleted_at !== null;
}

export function CustomerTable({
  items,
  onEdit,
  onArchive,
  onRestore,
  onOpenDetail,
  onCreate,
  archivingId,
  restoringId,
}: CustomerTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={uiLabels.emptyCustomersTitle}
        description={uiLabels.emptyCustomersDescription}
        actionLabel={onCreate ? uiLabels.createNew : undefined}
        onAction={onCreate}
      />
    );
  }

  return (
    <DataTable>
      <thead>
        <tr>
          <th>{labels.display_name}</th>
          <th>{labels.city}</th>
          <th>{labels.customer_type}</th>
          <th>{labels.status}</th>
          <th>{labels.phone}</th>
          <th>{labels.actions}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((c) => {
          const isArchived = isArchivedCustomer(c);
          return (
            <tr key={c.id} className={isArchived ? "row-archived" : undefined}>
              <td>
                {onOpenDetail ? (
                  <button
                    type="button"
                    className="btn link name-link"
                    onClick={() => onOpenDetail(c)}
                  >
                    <strong>{c.display_name}</strong>
                  </button>
                ) : (
                  <strong>{c.display_name}</strong>
                )}
                {c.trade_name && <div className="muted">{c.trade_name}</div>}
              </td>
              <td>{c.city ?? "—"}</td>
              <td>{customerTypeLabels[c.customer_type] ?? c.customer_type}</td>
              <td>
                <Badge variant={customerStatusBadgeVariant(c.status)}>
                  {customerStatusLabels[c.status] ?? c.status}
                </Badge>
              </td>
              <td>{c.phone ?? "—"}</td>
              <td className="actions">
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
              </td>
            </tr>
          );
        })}
      </tbody>
    </DataTable>
  );
}

// Re-export Modal from ui for backward compatibility
export { Modal } from "./ui/Modal";
