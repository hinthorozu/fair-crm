import React from "react";
import type { Contact } from "../types/contact";
import { contactLabels } from "../labels/contactLabels";
import { labels } from "../labels";

interface ContactTableProps {
  items: Contact[];
  deletingId: string | null;
  onEdit: (contact: Contact) => void;
  onDelete: (contact: Contact) => void;
}

function formatPhone(contact: Contact): string {
  return contact.mobile_phone || contact.phone || "—";
}

export function ContactTable({ items, deletingId, onEdit, onDelete }: ContactTableProps) {
  if (items.length === 0) {
    return <p className="empty">{contactLabels.noContacts}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="customer-table">
        <thead>
          <tr>
            <th>{contactLabels.fullName}</th>
            <th>{contactLabels.title}</th>
            <th>{contactLabels.department}</th>
            <th>{contactLabels.email}</th>
            <th>{contactLabels.phone}</th>
            <th>{contactLabels.actions}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>
                <strong>{c.full_name}</strong>
                {c.is_primary && (
                  <span className="badge status-active" style={{ marginLeft: "0.5rem" }}>
                    {contactLabels.primaryBadge}
                  </span>
                )}
              </td>
              <td>{c.title ?? "—"}</td>
              <td>{c.department ?? "—"}</td>
              <td>{c.email ?? "—"}</td>
              <td>{formatPhone(c)}</td>
              <td className="actions">
                <button type="button" className="btn link" onClick={() => onEdit(c)}>
                  {contactLabels.edit}
                </button>
                <button
                  type="button"
                  className="btn link danger"
                  disabled={deletingId === c.id}
                  onClick={() => onDelete(c)}
                >
                  {deletingId === c.id ? labels.loading : contactLabels.delete}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
