import React from "react";
import {
  createActivity,
  deleteActivity,
  listActivitiesByCustomer,
  updateActivity,
} from "../api/activities";
import {
  createParticipation,
  deleteParticipation,
  getParticipation,
  listParticipationsByCustomer,
  updateParticipation,
} from "../api/participations";
import { listFairs } from "../api/fairs";
import { getCustomer } from "../api/customers";
import {
  createContact,
  deleteContact,
  listContactsByCustomer,
  updateContact,
} from "../api/contacts";
import { ApiError } from "../api/client";
import {
  ActivityForm,
  activityToFormValues,
  type ActivityFormValues,
} from "../components/ActivityForm";
import { ActivityTable } from "../components/ActivityList";
import { ContactForm, contactToFormValues, type ContactFormValues } from "../components/ContactForm";
import { ContactTable } from "../components/ContactList";
import {
  CustomerParticipationTable,
} from "../components/ParticipationList";
import {
  ParticipationForm,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
  participationToFormValues,
  type ParticipationFormValues,
} from "../components/ParticipationForm";
import { PaginationBar } from "../components/Pagination";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState, TableSkeleton } from "../components/ui/LoadingState";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { activityLabels } from "../labels/activityLabels";
import { contactLabels } from "../labels/contactLabels";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { participationLabels } from "../labels/participationLabels";
import type { Activity } from "../types/activity";
import type { Customer } from "../types/customer";
import type { Contact } from "../types/contact";
import type { Fair } from "../types/fair";
import type { CustomerParticipationListItem } from "../types/participation";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";
import { customerStatusBadgeVariant } from "../utils/badges";

interface CustomerDetailPageProps {
  customerId: string;
  onBack: () => void;
  onCustomerLoaded?: (name: string) => void;
}

type TabId = "overview" | "contacts" | "activities" | "participations";

type ConfirmState =
  | { type: "contact"; item: Contact }
  | { type: "activity"; item: Activity }
  | { type: "participation"; item: CustomerParticipationListItem }
  | null;

export function CustomerDetailPage({
  customerId,
  onBack,
  onCustomerLoaded,
}: CustomerDetailPageProps) {
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [contacts, setContacts] = React.useState<Contact[]>([]);
  const [activities, setActivities] = React.useState<Activity[]>([]);
  const [participations, setParticipations] = React.useState<CustomerParticipationListItem[]>([]);
  const [fairs, setFairs] = React.useState<Fair[]>([]);
  const [activeTab, setActiveTab] = React.useState<TabId>("overview");
  const [loading, setLoading] = React.useState(true);
  const [contactsLoading, setContactsLoading] = React.useState(false);
  const [activitiesLoading, setActivitiesLoading] = React.useState(false);
  const [participationsLoading, setParticipationsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [contactsPage, setContactsPage] = React.useState(DEFAULT_PAGE);
  const [contactsPageSize, setContactsPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [contactsTotal, setContactsTotal] = React.useState(0);
  const [contactsTotalPages, setContactsTotalPages] = React.useState(0);
  const [activitiesPage, setActivitiesPage] = React.useState(DEFAULT_PAGE);
  const [activitiesPageSize, setActivitiesPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [activitiesTotal, setActivitiesTotal] = React.useState(0);
  const [activitiesTotalPages, setActivitiesTotalPages] = React.useState(0);
  const [participationsPage, setParticipationsPage] = React.useState(DEFAULT_PAGE);
  const [participationsPageSize, setParticipationsPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [participationsTotal, setParticipationsTotal] = React.useState(0);
  const [participationsTotalPages, setParticipationsTotalPages] = React.useState(0);
  const [modal, setModal] = React.useState<
    | "create-contact"
    | "edit-contact"
    | "create-activity"
    | "edit-activity"
    | "create-participation"
    | "edit-participation"
    | null
  >(null);
  const [editingContact, setEditingContact] = React.useState<Contact | null>(null);
  const [editingActivity, setEditingActivity] = React.useState<Activity | null>(null);
  const [editingParticipation, setEditingParticipation] =
    React.useState<CustomerParticipationListItem | null>(null);
  const [participationFormInitial, setParticipationFormInitial] =
    React.useState<ParticipationFormValues | undefined>(undefined);
  const [deletingContactId, setDeletingContactId] = React.useState<string | null>(null);
  const [deletingActivityId, setDeletingActivityId] = React.useState<string | null>(null);
  const [deletingParticipationId, setDeletingParticipationId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmState>(null);

  const loadCustomer = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCustomer(customerId);
      setCustomer(data);
      onCustomerLoaded?.(data.display_name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Müşteri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [customerId, onCustomerLoaded]);

  const loadContacts = React.useCallback(async () => {
    setContactsLoading(true);
    try {
      const res = await listContactsByCustomer(customerId, {
        page: contactsPage,
        page_size: contactsPageSize,
      });
      setContacts(res.items);
      setContactsTotal(res.total);
      setContactsTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : contactLabels.loadError);
    } finally {
      setContactsLoading(false);
    }
  }, [customerId, contactsPage, contactsPageSize]);

  const loadContactsForForm = React.useCallback(async () => {
    try {
      const res = await listContactsByCustomer(customerId, { page: 1, page_size: 100 });
      setContacts(res.items);
    } catch {
      // best-effort for form dropdown
    }
  }, [customerId]);

  const loadActivities = React.useCallback(async () => {
    setActivitiesLoading(true);
    try {
      const res = await listActivitiesByCustomer(customerId, {
        page: activitiesPage,
        page_size: activitiesPageSize,
      });
      setActivities(res.items);
      setActivitiesTotal(res.total);
      setActivitiesTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : activityLabels.loadError);
    } finally {
      setActivitiesLoading(false);
    }
  }, [customerId, activitiesPage, activitiesPageSize]);

  const loadParticipations = React.useCallback(async () => {
    setParticipationsLoading(true);
    try {
      const res = await listParticipationsByCustomer(customerId, {
        page: participationsPage,
        page_size: participationsPageSize,
      });
      setParticipations(res.items);
      setParticipationsTotal(res.total);
      setParticipationsTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.loadError);
    } finally {
      setParticipationsLoading(false);
    }
  }, [customerId, participationsPage, participationsPageSize]);

  const loadFairsForForm = React.useCallback(async () => {
    try {
      const res = await listFairs({ page: 1, page_size: 100, status: "planned" });
      const active = await listFairs({ page: 1, page_size: 100, status: "active" });
      const completed = await listFairs({ page: 1, page_size: 100, status: "completed" });
      setFairs([...res.items, ...active.items, ...completed.items]);
    } catch {
      // best-effort
    }
  }, []);

  React.useEffect(() => {
    void loadCustomer();
  }, [loadCustomer]);

  React.useEffect(() => {
    if (!customer) return;
    void listContactsByCustomer(customerId, { page: 1, page_size: 1 }).then((res) => {
      setContactsTotal(res.total);
    });
    void listActivitiesByCustomer(customerId, { page: 1, page_size: 1 }).then((res) => {
      setActivitiesTotal(res.total);
    });
    void listParticipationsByCustomer(customerId, { page: 1, page_size: 1 }).then((res) => {
      setParticipationsTotal(res.total);
    });
  }, [customerId, customer]);

  React.useEffect(() => {
    if (activeTab === "contacts") void loadContacts();
  }, [activeTab, loadContacts]);

  React.useEffect(() => {
    if (activeTab === "activities") {
      void loadActivities();
      void loadContactsForForm();
    }
  }, [activeTab, loadActivities, loadContactsForForm]);

  React.useEffect(() => {
    if (activeTab === "participations") {
      void loadParticipations();
      void loadFairsForForm();
      void loadContactsForForm();
    }
  }, [activeTab, loadParticipations, loadFairsForForm, loadContactsForForm]);

  const handleCreateContact = async (values: ContactFormValues) => {
    await createContact({ customer_id: customerId, ...values });
    setModal(null);
    await loadContacts();
  };

  const handleUpdateContact = async (values: ContactFormValues) => {
    if (!editingContact) return;
    await updateContact(editingContact.id, values);
    setModal(null);
    setEditingContact(null);
    await loadContacts();
  };

  const handleDeleteContact = async (contact: Contact) => {
    setDeletingContactId(contact.id);
    setError(null);
    try {
      await deleteContact(contact.id);
      await loadContacts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : contactLabels.deleteError);
    } finally {
      setDeletingContactId(null);
      setConfirm(null);
    }
  };

  const handleCreateActivity = async (values: ActivityFormValues) => {
    await createActivity({ customer_id: customerId, ...values });
    setModal(null);
    setActivitiesPage(DEFAULT_PAGE);
    await loadActivities();
  };

  const handleUpdateActivity = async (values: ActivityFormValues) => {
    if (!editingActivity) return;
    await updateActivity(editingActivity.id, values);
    setModal(null);
    setEditingActivity(null);
    await loadActivities();
  };

  const handleDeleteActivity = async (activity: Activity) => {
    setDeletingActivityId(activity.id);
    setError(null);
    try {
      await deleteActivity(activity.id);
      await loadActivities();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : activityLabels.deleteError);
    } finally {
      setDeletingActivityId(null);
      setConfirm(null);
    }
  };

  const handleCreateParticipation = async (values: ParticipationFormValues) => {
    await createParticipation(formValuesToCreatePayload(values, "customer", customerId));
    setModal(null);
    setParticipationsPage(DEFAULT_PAGE);
    await loadParticipations();
  };

  const handleUpdateParticipation = async (values: ParticipationFormValues) => {
    if (!editingParticipation) return;
    await updateParticipation(editingParticipation.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditingParticipation(null);
    setParticipationFormInitial(undefined);
    await loadParticipations();
  };

  const handleDeleteParticipation = async (item: CustomerParticipationListItem) => {
    setDeletingParticipationId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      await loadParticipations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingParticipationId(null);
      setConfirm(null);
    }
  };

  const openEditParticipation = async (item: CustomerParticipationListItem) => {
    try {
      const full = await getParticipation(item.id);
      setParticipationFormInitial(participationToFormValues(full));
      setEditingParticipation(item);
      setModal("edit-participation");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.loadError);
    }
  };

  const openCreateModal = () => {
    if (activeTab === "contacts") {
      setEditingContact(null);
      setModal("create-contact");
    } else if (activeTab === "activities") {
      setEditingActivity(null);
      setModal("create-activity");
    } else if (activeTab === "participations") {
      setEditingParticipation(null);
      setParticipationFormInitial(undefined);
      setModal("create-participation");
    }
  };

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    {
      id: "contacts" as const,
      label: uiLabels.tabContacts,
      badge: contactsTotal > 0 ? contactsTotal : undefined,
    },
    {
      id: "activities" as const,
      label: uiLabels.tabActivities,
      badge: activitiesTotal > 0 ? activitiesTotal : undefined,
    },
    {
      id: "participations" as const,
      label: uiLabels.tabFairParticipations,
      badge: participationsTotal > 0 ? participationsTotal : undefined,
    },
  ];

  if (loading) {
    return <LoadingState />;
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

  const showNewButton =
    activeTab === "contacts" || activeTab === "activities" || activeTab === "participations";
  const newButtonLabel =
    activeTab === "contacts"
      ? contactLabels.newContact
      : activeTab === "activities"
        ? activityLabels.newActivity
        : participationLabels.addToFair;

  return (
    <div className="page">
      <PageHeader
        title={customer.display_name}
        subtitle={
          <>
            <Badge variant="neutral">
              {customerTypeLabels[customer.customer_type] ?? customer.customer_type}
            </Badge>
            {" · "}
            <Badge variant={customerStatusBadgeVariant(customer.status)}>
              {customerStatusLabels[customer.status] ?? customer.status}
            </Badge>
          </>
        }
        backAction={
          <button type="button" className="btn link back-link" onClick={onBack}>
            ← {contactLabels.backToCustomers}
          </button>
        }
        actions={
          showNewButton ? (
            <button type="button" className="btn primary" onClick={openCreateModal}>
              {newButtonLabel}
            </button>
          ) : undefined
        }
      />

      <Tabs items={tabItems} active={activeTab} onChange={setActiveTab} />

      {error && <div className="banner error">{error}</div>}

      <TabPanel id="panel-overview" labelledBy="tab-overview" active={activeTab === "overview"}>
        <Card>
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
        </Card>
      </TabPanel>

      <TabPanel id="panel-contacts" labelledBy="tab-contacts" active={activeTab === "contacts"}>
        <PaginationBar
          page={contactsPage}
          pageSize={contactsPageSize}
          total={contactsTotal}
          totalPages={contactsTotalPages}
          loading={contactsLoading}
          onPageChange={setContactsPage}
          onPageSizeChange={(size) => {
            setContactsPage(DEFAULT_PAGE);
            setContactsPageSize(size);
          }}
        />
        {contactsLoading ? (
          <TableSkeleton rows={4} cols={6} />
        ) : (
          <ContactTable
            items={contacts}
            deletingId={deletingContactId}
            onCreate={openCreateModal}
            onEdit={(c) => {
              setEditingContact(c);
              setModal("edit-contact");
            }}
            onDelete={(c) => setConfirm({ type: "contact", item: c })}
          />
        )}
      </TabPanel>

      <TabPanel id="panel-activities" labelledBy="tab-activities" active={activeTab === "activities"}>
        <PaginationBar
          page={activitiesPage}
          pageSize={activitiesPageSize}
          total={activitiesTotal}
          totalPages={activitiesTotalPages}
          loading={activitiesLoading}
          onPageChange={setActivitiesPage}
          onPageSizeChange={(size) => {
            setActivitiesPage(DEFAULT_PAGE);
            setActivitiesPageSize(size);
          }}
        />
        {activitiesLoading ? (
          <LoadingState variant="card" />
        ) : (
          <ActivityTable
            items={activities}
            deletingId={deletingActivityId}
            onCreate={openCreateModal}
            onEdit={(a) => {
              setEditingActivity(a);
              setModal("edit-activity");
            }}
            onDelete={(a) => setConfirm({ type: "activity", item: a })}
          />
        )}
      </TabPanel>

      <TabPanel
        id="panel-participations"
        labelledBy="tab-participations"
        active={activeTab === "participations"}
      >
        <PaginationBar
          page={participationsPage}
          pageSize={participationsPageSize}
          total={participationsTotal}
          totalPages={participationsTotalPages}
          loading={participationsLoading}
          onPageChange={setParticipationsPage}
          onPageSizeChange={(size) => {
            setParticipationsPage(DEFAULT_PAGE);
            setParticipationsPageSize(size);
          }}
        />
        {participationsLoading ? (
          <TableSkeleton rows={4} cols={7} />
        ) : (
          <CustomerParticipationTable
            items={participations}
            deletingId={deletingParticipationId}
            onCreate={openCreateModal}
            onEdit={(item) => void openEditParticipation(item)}
            onDelete={(item) => setConfirm({ type: "participation", item })}
          />
        )}
      </TabPanel>

      {modal === "create-contact" && (
        <Modal title={contactLabels.newContact} onClose={() => setModal(null)}>
          <ContactForm
            submitLabel={contactLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreateContact}
          />
        </Modal>
      )}

      {modal === "edit-contact" && editingContact && (
        <Modal title={contactLabels.editContact} onClose={() => setModal(null)}>
          <ContactForm
            initial={contactToFormValues(editingContact)}
            submitLabel={contactLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdateContact}
          />
        </Modal>
      )}

      {modal === "create-activity" && (
        <Modal title={activityLabels.newActivity} onClose={() => setModal(null)} size="lg">
          <ActivityForm
            contacts={contacts}
            submitLabel={activityLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreateActivity}
          />
        </Modal>
      )}

      {modal === "edit-activity" && editingActivity && (
        <Modal title={activityLabels.editActivity} onClose={() => setModal(null)} size="lg">
          <ActivityForm
            contacts={contacts}
            initial={activityToFormValues(editingActivity)}
            submitLabel={activityLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdateActivity}
          />
        </Modal>
      )}

      {modal === "create-participation" && (
        <Modal title={participationLabels.newParticipation} onClose={() => setModal(null)} size="lg">
          <ParticipationForm
            mode="customer"
            fairs={fairs}
            contacts={contacts}
            submitLabel={participationLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreateParticipation}
          />
        </Modal>
      )}

      {modal === "edit-participation" && editingParticipation && participationFormInitial && (
        <Modal title={participationLabels.editParticipation} onClose={() => setModal(null)} size="lg">
          <ParticipationForm
            mode="customer"
            fairs={fairs}
            contacts={contacts}
            initial={participationFormInitial}
            submitLabel={participationLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdateParticipation}
          />
        </Modal>
      )}

      {confirm?.type === "contact" && (
        <ConfirmDialog
          title={uiLabels.deleteContactTitle}
          message={contactLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingContactId === confirm.item.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleDeleteContact(confirm.item)}
        />
      )}

      {confirm?.type === "activity" && (
        <ConfirmDialog
          title={uiLabels.deleteActivityTitle}
          message={activityLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingActivityId === confirm.item.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleDeleteActivity(confirm.item)}
        />
      )}

      {confirm?.type === "participation" && (
        <ConfirmDialog
          title={uiLabels.delete}
          message={participationLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingParticipationId === confirm.item.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleDeleteParticipation(confirm.item)}
        />
      )}
    </div>
  );
}
