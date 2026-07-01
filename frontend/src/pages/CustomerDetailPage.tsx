import React from "react";
import { getCustomer } from "../api/customers";
import {
  createContact,
  deleteContact,
  listContactsByCustomer,
  updateContact,
} from "../api/contacts";
import { ApiError } from "../api/client";
import { ContactForm, contactToFormValues, type ContactFormValues } from "../components/ContactForm";
import { ContactTable } from "../components/ContactList";
import { Modal } from "../components/CustomerList";
import { PaginationBar } from "../components/Pagination";
import { contactLabels } from "../labels/contactLabels";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";
import type { Customer } from "../types/customer";
import type { Contact } from "../types/contact";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

interface CustomerDetailPageProps {
  customerId: string;
  onBack: () => void;
}

type TabId = "overview" | "contacts";

export function CustomerDetailPage({ customerId, onBack }: CustomerDetailPageProps) {
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [contacts, setContacts] = React.useState<Contact[]>([]);
  const [activeTab, setActiveTab] = React.useState<TabId>("contacts");
  const [loading, setLoading] = React.useState(true);
  const [contactsLoading, setContactsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [page, setPage] = React.useState(DEFAULT_PAGE);
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Contact | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  const loadCustomer = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCustomer(customerId);
      setCustomer(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Müşteri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  const loadContacts = React.useCallback(async () => {
    setContactsLoading(true);
    try {
      const res = await listContactsByCustomer(customerId, { page, page_size: pageSize });
      setContacts(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : contactLabels.loadError);
    } finally {
      setContactsLoading(false);
    }
  }, [customerId, page, pageSize]);

  React.useEffect(() => {
    void loadCustomer();
  }, [loadCustomer]);

  React.useEffect(() => {
    if (activeTab === "contacts") {
      void loadContacts();
    }
  }, [activeTab, loadContacts]);

  const handleCreate = async (values: ContactFormValues) => {
    await createContact({ customer_id: customerId, ...values });
    setModal(null);
    setPage(DEFAULT_PAGE);
    await loadContacts();
  };

  const handleUpdate = async (values: ContactFormValues) => {
    if (!editing) return;
    await updateContact(editing.id, values);
    setModal(null);
    setEditing(null);
    await loadContacts();
  };

  const handleDelete = async (contact: Contact) => {
    if (!window.confirm(contactLabels.deleteConfirm)) return;
    setDeletingId(contact.id);
    setError(null);
    try {
      await deleteContact(contact.id);
      await loadContacts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : contactLabels.deleteError);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return <div className="loading">{labels.loading}</div>;
  }

  if (!customer) {
    return (
      <div className="page">
        <div className="banner error">{error ?? "Müşteri bulunamadı."}</div>
        <button type="button" className="btn secondary" onClick={onBack}>
          {contactLabels.backToCustomers}
        </button>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <button type="button" className="btn link back-link" onClick={onBack}>
            ← {contactLabels.backToCustomers}
          </button>
          <h1>{customer.display_name}</h1>
          <p className="muted">
            {customerTypeLabels[customer.customer_type] ?? customer.customer_type} ·{" "}
            {customerStatusLabels[customer.status] ?? customer.status}
          </p>
        </div>
        {activeTab === "contacts" && (
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setEditing(null);
              setModal("create");
            }}
          >
            {contactLabels.newContact}
          </button>
        )}
      </header>

      <div className="tabs">
        <button
          type="button"
          className={activeTab === "overview" ? "tab active" : "tab"}
          onClick={() => setActiveTab("overview")}
        >
          {contactLabels.tabOverview}
        </button>
        <button
          type="button"
          className={activeTab === "contacts" ? "tab active" : "tab"}
          onClick={() => setActiveTab("contacts")}
        >
          {contactLabels.tabContacts}
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      {activeTab === "overview" && (
        <div className="detail-card">
          <dl className="detail-grid">
            <div>
              <dt>{labels.display_name}</dt>
              <dd>{customer.display_name}</dd>
            </div>
            <div>
              <dt>{labels.city}</dt>
              <dd>{customer.city ?? "—"}</dd>
            </div>
            <div>
              <dt>{labels.phone}</dt>
              <dd>{customer.phone ?? "—"}</dd>
            </div>
            <div>
              <dt>{labels.email}</dt>
              <dd>{customer.email ?? "—"}</dd>
            </div>
            <div className="full-width">
              <dt>{labels.address}</dt>
              <dd>{customer.address ?? "—"}</dd>
            </div>
            <div className="full-width">
              <dt>{labels.description}</dt>
              <dd>{customer.description ?? "—"}</dd>
            </div>
          </dl>
        </div>
      )}

      {activeTab === "contacts" && (
        <>
          <PaginationBar
            page={page}
            pageSize={pageSize}
            total={total}
            totalPages={totalPages}
            loading={contactsLoading}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPage(DEFAULT_PAGE);
              setPageSize(size);
            }}
          />

          {contactsLoading ? (
            <div className="loading">{labels.loading}</div>
          ) : (
            <ContactTable
              items={contacts}
              deletingId={deletingId}
              onEdit={(c) => {
                setEditing(c);
                setModal("edit");
              }}
              onDelete={(c) => void handleDelete(c)}
            />
          )}
        </>
      )}

      {modal === "create" && (
        <Modal title={contactLabels.newContact} onClose={() => setModal(null)}>
          <ContactForm
            submitLabel={contactLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreate}
          />
        </Modal>
      )}

      {modal === "edit" && editing && (
        <Modal title={contactLabels.editContact} onClose={() => setModal(null)}>
          <ContactForm
            initial={contactToFormValues(editing)}
            submitLabel={contactLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdate}
          />
        </Modal>
      )}
    </div>
  );
}
