import React from "react";
import type { Contact } from "../types/contact";
import { contactLabels } from "../labels/contactLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import { TableRowActions } from "./ui/TableRowActions";

interface ContactTableProps {
  items: Contact[];
  deletingId: string | null;
  onEdit: (contact: Contact) => void;
  onDelete: (contact: Contact) => void;
  onCreate?: () => void;
  emptyDueToFilters?: boolean;
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
}

function formatPhone(contact: Contact): string {
  return contact.mobile_phone || contact.phone || "—";
}

function buildContactColumns(props: ContactTableProps): UniversalDataTableColumn<Contact>[] {
  const { onEdit, onDelete, deletingId } = props;
  return [
    {
      key: "full_name",
      title: contactLabels.fullName,
      sortable: true,
      render: (c) => (
        <>
          <strong>{c.full_name}</strong>
          {c.is_primary && (
            <Badge variant="success" className="badge-inline">
              {contactLabels.primaryBadge}
            </Badge>
          )}
        </>
      ),
    },
    {
      key: "title",
      title: contactLabels.title,
      sortable: true,
      render: (c) => c.title ?? "—",
    },
    {
      key: "department",
      title: contactLabels.department,
      sortable: true,
      render: (c) => c.department ?? "—",
    },
    {
      key: "email",
      title: contactLabels.email,
      sortable: true,
      render: (c) => c.email ?? "—",
    },
    {
      key: "phone",
      title: contactLabels.phone,
      sortable: true,
      render: (c) => formatPhone(c),
    },
    {
      key: "actions",
      title: contactLabels.actions,
      sortable: false,
      className: "actions",
      render: (c) => (
        <TableRowActions>
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
        </TableRowActions>
      ),
    },
  ];
}

export function ContactTable(props: ContactTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;

  return (
    <UniversalDataTable
      columns={buildContactColumns(props)}
      items={items}
      rowKey={(c) => c.id}
      sorting={{ field: sortField ?? null, direction: sortDirection ?? null }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : uiLabels.emptyContactsTitle}
          description={
            emptyDueToFilters ? uiLabels.emptySearchDescription : uiLabels.emptyContactsDescription
          }
          actionLabel={onCreate ? uiLabels.createNew : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}
