import React from "react";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";

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
        placeholder={labels.searchPlaceholder}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as CustomerStatus | "")}
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
  archivingId,
  restoringId,
}: CustomerTableProps) {
  if (items.length === 0) {
    return <p className="empty">{labels.noResults}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="customer-table">
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
                <span className={`badge status-${c.status}`}>
                  {customerStatusLabels[c.status] ?? c.status}
                </span>
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
      </table>
    </div>
  );
}

interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, onClose, children }: ModalProps) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button type="button" className="btn icon" onClick={onClose} aria-label={labels.cancel}>
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
