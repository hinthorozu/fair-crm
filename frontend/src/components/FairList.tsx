import React from "react";
import type { Fair, FairStatus } from "../types/fair";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { labels } from "../labels";

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
        placeholder={fairLabels.searchPlaceholder}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as FairStatus | "")}
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
  archivingId: string | null;
  restoringId: string | null;
}

function isArchivedFair(fair: Fair): boolean {
  return fair.status === "archived" || fair.deleted_at !== null;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return value;
}

export function FairTable({
  items,
  onEdit,
  onArchive,
  onRestore,
  archivingId,
  restoringId,
}: FairTableProps) {
  if (items.length === 0) {
    return <p className="empty">{fairLabels.noResults}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="customer-table">
        <thead>
          <tr>
            <th>{fairLabels.name}</th>
            <th>{fairLabels.organizer}</th>
            <th>{fairLabels.venue}</th>
            <th>{labels.city}</th>
            <th>{fairLabels.start_date}</th>
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
                  <strong>{f.name}</strong>
                  {f.country && <div className="muted">{f.country}</div>}
                </td>
                <td>{f.organizer ?? "—"}</td>
                <td>{f.venue ?? "—"}</td>
                <td>{f.city ?? "—"}</td>
                <td>{formatDate(f.start_date)}</td>
                <td>
                  <span className={`badge status-${f.status}`}>
                    {fairStatusLabels[f.status] ?? f.status}
                  </span>
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
        aria-labelledby="fair-modal-title"
      >
        <header className="modal-header">
          <h2 id="fair-modal-title">{title}</h2>
          <button type="button" className="btn icon" onClick={onClose} aria-label={labels.cancel}>
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
