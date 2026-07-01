import React from "react";
import type { Contact } from "../types/contact";
import { contactLabels } from "../labels/contactLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { DataTable } from "./ui/DataTable";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";

interface ContactTableProps {
  items: Contact[];
  deletingId: string | null;
  onEdit: (contact: Contact) => void;
  onDelete: (contact: Contact) => void;
  onCreate?: () => void;
}

function formatPhone(contact: Contact): string {
  return contact.mobile_phone || contact.phone || "—";
}

export function ContactTable({
  items,
  deletingId,
  onEdit,
  onDelete,
  onCreate,
}: ContactTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<EmptyStateIcon />}
        title={uiLabels.emptyContactsTitle}
        description={uiLabels.emptyContactsDescription}
        actionLabel={uiLabels.createNew}
        onAction={onCreate}
      />
    );
  }

  return (
    <DataTable>
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
                <Badge variant="success" className="badge-inline">
                  {contactLabels.primaryBadge}
                </Badge>
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
    </DataTable>
  );
}
