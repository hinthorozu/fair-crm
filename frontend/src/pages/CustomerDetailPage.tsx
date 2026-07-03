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
import { getCustomer, archiveCustomer, updateCustomer } from "../api/customers";
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
import { CustomerForm, customerToFormValues } from "../components/CustomerForm";
import type { CreateCustomerPayload } from "../types/customer";
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
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState } from "../components/ui/LoadingState";
import { Modal } from "../components/ui/Modal";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import {
  DetailEmailList,
  DetailPhoneList,
  DetailValue,
  DetailWebsiteList,
} from "../components/ui/DetailFields";
import { activityLabels } from "../labels/activityLabels";
import { contactLabels } from "../labels/contactLabels";
import { customerStatusLabels, customerTypeLabels, customerSourceLabels, labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { participationLabels } from "../labels/participationLabels";
import type { Activity } from "../types/activity";
import type { Customer } from "../types/customer";
import type { Contact } from "../types/contact";
import type { Fair } from "../types/fair";
import type { CustomerParticipationListItem } from "../types/participation";
import { customerStatusBadgeVariant } from "../utils/badges";
import {
  buildLocationSearch,
  navigateWithSearch,
  readSearchParams,
} from "../utils/urlState";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";

interface CustomerDetailPageProps {
  customerId: string;
  onBack: () => void;
  onCustomerLoaded?: (name: string) => void;
}

type TabId = "overview" | "contacts" | "activities" | "participations";

const VALID_TABS: TabId[] = ["overview", "contacts", "activities", "participations"];

function tabFromUrl(): TabId {
  const tab = readSearchParams().get("tab");
  if (tab && VALID_TABS.includes(tab as TabId)) return tab as TabId;
  return "overview";
}

type ConfirmState =
  | { type: "contact"; item: Contact }
  | { type: "activity"; item: Activity }
  | { type: "participation"; item: CustomerParticipationListItem }
  | { type: "archive" }
  | null;

export function CustomerDetailPage({
  customerId,
  onBack,
  onCustomerLoaded,
}: CustomerDetailPageProps) {
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [contactsForForm, setContactsForForm] = React.useState<Contact[]>([]);
  const [fairs, setFairs] = React.useState<Fair[]>([]);
  const [activeTab, setActiveTabState] = React.useState<TabId>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [contactsTotal, setContactsTotal] = React.useState(0);
  const [activitiesTotal, setActivitiesTotal] = React.useState(0);
  const [participationsTotal, setParticipationsTotal] = React.useState(0);
  const [modal, setModal] = React.useState<
    | "edit-customer"
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
  const [archiving, setArchiving] = React.useState(false);
  const [confirm, setConfirm] = React.useState<ConfirmState>(null);

  const closeModal = React.useCallback(() => setModal(null), []);
  const closeConfirm = React.useCallback(() => setConfirm(null), []);

  const detailPath = `/customers/${customerId}`;

  const contactsTable = useServerDataTable<Contact>({
    fetchFn: (params) => listContactsByCustomer(customerId, params),
    defaultSort: { field: "first_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: activeTab === "contacts" && Boolean(customer),
  });

  const activitiesTable = useServerDataTable<Activity>({
    fetchFn: (params) => listActivitiesByCustomer(customerId, params),
    defaultSort: { field: "activity_date", direction: "desc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: activeTab === "activities" && Boolean(customer),
  });

  const participationsTable = useServerDataTable<CustomerParticipationListItem>({
    fetchFn: (params) => listParticipationsByCustomer(customerId, params),
    defaultSort: { field: "fair_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: activeTab === "participations" && Boolean(customer),
  });

  const setActiveTab = React.useCallback((tab: TabId) => {
    setActiveTabState(tab);
    const params = readSearchParams();
    if (tab === "overview") params.delete("tab");
    else params.set("tab", tab);
    navigateWithSearch(detailPath, buildLocationSearch(params));
  }, [detailPath]);

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

  const loadContactsForForm = React.useCallback(async () => {
    try {
      const res = await listContactsByCustomer(customerId, { page: 1, pageSize: 100 });
      setContactsForForm(res.items);
    } catch {
      // best-effort for form dropdown
    }
  }, [customerId]);

  const loadFairsForForm = React.useCallback(async () => {
    try {
      const res = await listFairs({ page: 1, pageSize: 100, status: "planned" });
      const active = await listFairs({ page: 1, pageSize: 100, status: "active" });
      const completed = await listFairs({ page: 1, pageSize: 100, status: "completed" });
      setFairs([...res.items, ...active.items, ...completed.items]);
    } catch {
      // best-effort
    }
  }, []);

  React.useEffect(() => {
    void loadCustomer();
  }, [loadCustomer]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  React.useEffect(() => {
    if (!customer) return;
    void listContactsByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
      setContactsTotal(res.pagination.totalItems);
    });
    void listActivitiesByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
      setActivitiesTotal(res.pagination.totalItems);
    });
    void listParticipationsByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
      setParticipationsTotal(res.pagination.totalItems);
    });
  }, [customerId, customer]);

  React.useEffect(() => {
    if (activeTab === "activities" || activeTab === "participations") {
      void loadContactsForForm();
    }
  }, [activeTab, loadContactsForForm]);

  React.useEffect(() => {
    if (activeTab === "participations") {
      void loadFairsForForm();
    }
  }, [activeTab, loadFairsForForm]);

  React.useEffect(() => {
    if (activeTab === "contacts") {
      setContactsTotal(contactsTable.pagination.totalItems);
    }
  }, [activeTab, contactsTable.pagination.totalItems]);

  React.useEffect(() => {
    if (activeTab === "activities") {
      setActivitiesTotal(activitiesTable.pagination.totalItems);
    }
  }, [activeTab, activitiesTable.pagination.totalItems]);

  React.useEffect(() => {
    if (activeTab === "participations") {
      setParticipationsTotal(participationsTable.pagination.totalItems);
    }
  }, [activeTab, participationsTable.pagination.totalItems]);

  const handleCreateContact = async (values: ContactFormValues) => {
    await createContact({ customer_id: customerId, ...values });
    setModal(null);
    await contactsTable.refresh();
  };

  const handleUpdateContact = async (values: ContactFormValues) => {
    if (!editingContact) return;
    await updateContact(editingContact.id, values);
    setModal(null);
    setEditingContact(null);
    await contactsTable.refresh();
  };

  const handleDeleteContact = async (contact: Contact) => {
    setDeletingContactId(contact.id);
    setError(null);
    try {
      await deleteContact(contact.id);
      await contactsTable.refresh();
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
    await activitiesTable.refresh();
  };

  const handleUpdateActivity = async (values: ActivityFormValues) => {
    if (!editingActivity) return;
    await updateActivity(editingActivity.id, values);
    setModal(null);
    setEditingActivity(null);
    await activitiesTable.refresh();
  };

  const handleDeleteActivity = async (activity: Activity) => {
    setDeletingActivityId(activity.id);
    setError(null);
    try {
      await deleteActivity(activity.id);
      await activitiesTable.refresh();
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
    await participationsTable.refresh();
  };

  const handleUpdateParticipation = async (values: ParticipationFormValues) => {
    if (!editingParticipation) return;
    await updateParticipation(editingParticipation.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditingParticipation(null);
    setParticipationFormInitial(undefined);
    await participationsTable.refresh();
  };

  const handleDeleteParticipation = async (item: CustomerParticipationListItem) => {
    setDeletingParticipationId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      await participationsTable.refresh();
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

  const handleUpdateCustomer = async (values: CreateCustomerPayload) => {
    await updateCustomer(customerId, values);
    setModal(null);
    await loadCustomer();
  };

  const handleArchiveCustomer = async () => {
    setArchiving(true);
    setError(null);
    try {
      await archiveCustomer(customerId);
      setConfirm(null);
      onBack();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Arşivleme başarısız.");
    } finally {
      setArchiving(false);
    }
  };

  const openCreateContact = () => {
    setEditingContact(null);
    setModal("create-contact");
  };

  const openCreateActivity = () => {
    void loadContactsForForm();
    setEditingActivity(null);
    setModal("create-activity");
  };

  const openCreateParticipation = () => {
    void loadFairsForForm();
    void loadContactsForForm();
    setEditingParticipation(null);
    setParticipationFormInitial(undefined);
    setModal("create-participation");
  };

  const openCreateModal = () => {
    if (activeTab === "contacts") {
      openCreateContact();
    } else if (activeTab === "activities") {
      openCreateActivity();
    } else if (activeTab === "participations") {
      openCreateParticipation();
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

  const isArchived = customer.status === "archived" || customer.deleted_at !== null;

  const headerActions: PageHeaderAction[] = [
    {
      id: "edit",
      label: uiLabels.detailEdit,
      variant: "primary",
      onClick: () => setModal("edit-customer"),
      disabled: isArchived,
    },
    {
      id: "add-contact",
      label: uiLabels.detailAddContact,
      variant: "secondary",
      onClick: openCreateContact,
      disabled: isArchived,
    },
    {
      id: "add-participation",
      label: participationLabels.addToFair,
      variant: "secondary",
      onClick: openCreateParticipation,
      disabled: isArchived,
    },
    {
      id: "add-activity",
      label: uiLabels.detailNewActivity,
      variant: "secondary",
      onClick: openCreateActivity,
      disabled: isArchived,
    },
    {
      id: "archive",
      label: labels.archive,
      variant: "danger",
      onClick: () => setConfirm({ type: "archive" }),
      disabled: isArchived,
      loading: archiving,
    },
  ];

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
        breadcrumbs={[{ label: contactLabels.backToCustomers, onClick: onBack }]}
        actions={headerActions}
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
              <dt>{labels.legal_name}</dt>
              <dd>
                <DetailValue value={customer.legal_name} />
              </dd>
            </div>
            <div>
              <dt>{labels.trade_name}</dt>
              <dd>
                <DetailValue value={customer.trade_name} />
              </dd>
            </div>
            <div>
              <dt>{labels.customer_type}</dt>
              <dd>{customerTypeLabels[customer.customer_type] ?? customer.customer_type}</dd>
            </div>
            <div>
              <dt>{labels.phone}</dt>
              <dd>
                <DetailPhoneList items={customer.phones ?? []} />
              </dd>
            </div>
            <div>
              <dt>{labels.email}</dt>
              <dd>
                <DetailEmailList items={customer.emails ?? []} />
              </dd>
            </div>
            <div>
              <dt>{labels.website}</dt>
              <dd>
                <DetailWebsiteList items={customer.websites ?? []} />
              </dd>
            </div>
            <div>
              <dt>{labels.source}</dt>
              <dd>{customerSourceLabels[customer.source] ?? customer.source}</dd>
            </div>
            <div>
              <dt>{labels.country}</dt>
              <dd>
                <DetailValue value={customer.country} />
              </dd>
            </div>
            <div>
              <dt>{labels.city}</dt>
              <dd>
                <DetailValue value={customer.city} />
              </dd>
            </div>
            <div>
              <dt>{labels.district}</dt>
              <dd>
                <DetailValue value={customer.district} />
              </dd>
            </div>
            <div>
              <dt>{labels.tax_number}</dt>
              <dd>
                <DetailValue value={customer.tax_number} />
              </dd>
            </div>
            <div>
              <dt>{labels.tax_office}</dt>
              <dd>
                <DetailValue value={customer.tax_office} />
              </dd>
            </div>
            <div className="full-width">
              <dt>{labels.address}</dt>
              <dd>
                <DetailValue value={customer.address} />
              </dd>
            </div>
            <div className="full-width">
              <dt>{labels.description}</dt>
              <dd className="detail-multiline">
                <DetailValue value={customer.description} />
              </dd>
            </div>
          </dl>
        </Card>
      </TabPanel>

      <TabPanel id="panel-contacts" labelledBy="tab-contacts" active={activeTab === "contacts"}>
        <ServerDataTableFrame
          table={contactsTable}
          skeletonCols={6}
          toolbar={
            <div className="filters">
              <input
                type="search"
                className="search-input"
                placeholder={uiLabels.searchContact}
                value={contactsTable.search}
                onChange={(e) => contactsTable.setSearch(e.target.value)}
                aria-label={uiLabels.searchContact}
              />
              <button
                type="button"
                className="btn secondary"
                onClick={() => void contactsTable.refresh()}
              >
                {labels.refresh}
              </button>
            </div>
          }
        >
          <ContactTable
            items={contactsTable.items}
            deletingId={deletingContactId}
            emptyDueToFilters={contactsTable.hasActiveFilters}
            sortField={contactsTable.sorting.field}
            sortDirection={contactsTable.sorting.direction}
            onSortChange={contactsTable.setSort}
            onCreate={openCreateModal}
            onEdit={(c) => {
              setEditingContact(c);
              setModal("edit-contact");
            }}
            onDelete={(c) => setConfirm({ type: "contact", item: c })}
          />
        </ServerDataTableFrame>
      </TabPanel>

      <TabPanel id="panel-activities" labelledBy="tab-activities" active={activeTab === "activities"}>
        <ServerDataTableFrame
          table={activitiesTable}
          skeletonRows={4}
          toolbar={
            <div className="filters">
              <input
                type="search"
                className="search-input"
                placeholder={uiLabels.searchActivity}
                value={activitiesTable.search}
                onChange={(e) => activitiesTable.setSearch(e.target.value)}
                aria-label={uiLabels.searchActivity}
              />
              <button
                type="button"
                className="btn secondary"
                onClick={() => void activitiesTable.refresh()}
              >
                {labels.refresh}
              </button>
            </div>
          }
        >
          <ActivityTable
            items={activitiesTable.items}
            deletingId={deletingActivityId}
            emptyDueToFilters={activitiesTable.hasActiveFilters}
            sortField={activitiesTable.sorting.field}
            sortDirection={activitiesTable.sorting.direction}
            onSortChange={activitiesTable.setSort}
            onCreate={openCreateModal}
            onEdit={(a) => {
              setEditingActivity(a);
              setModal("edit-activity");
            }}
            onDelete={(a) => setConfirm({ type: "activity", item: a })}
          />
        </ServerDataTableFrame>
      </TabPanel>

      <TabPanel
        id="panel-participations"
        labelledBy="tab-participations"
        active={activeTab === "participations"}
      >
        <ServerDataTableFrame
          table={participationsTable}
          skeletonCols={7}
          toolbar={
            <div className="filters">
              <input
                type="search"
                className="search-input"
                placeholder={uiLabels.searchFair}
                value={participationsTable.search}
                onChange={(e) => participationsTable.setSearch(e.target.value)}
                aria-label={uiLabels.searchFair}
              />
              <button
                type="button"
                className="btn secondary"
                onClick={() => void participationsTable.refresh()}
              >
                {labels.refresh}
              </button>
            </div>
          }
        >
          <CustomerParticipationTable
            items={participationsTable.items}
            deletingId={deletingParticipationId}
            emptyDueToFilters={participationsTable.hasActiveFilters}
            sortField={participationsTable.sorting.field}
            sortDirection={participationsTable.sorting.direction}
            onSortChange={participationsTable.setSort}
            onCreate={openCreateModal}
            onEdit={(item) => void openEditParticipation(item)}
            onDelete={(item) => setConfirm({ type: "participation", item })}
          />
        </ServerDataTableFrame>
      </TabPanel>

      {modal === "edit-customer" && (
        <Modal title={labels.editCustomer} onClose={closeModal} size="lg">
          <CustomerForm
            initial={customerToFormValues(customer)}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateCustomer}
          />
        </Modal>
      )}

      {modal === "create-contact" && (
        <Modal title={contactLabels.newContact} onClose={closeModal}>
          <ContactForm
            submitLabel={contactLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateContact}
          />
        </Modal>
      )}

      {modal === "edit-contact" && editingContact && (
        <Modal title={contactLabels.editContact} onClose={closeModal}>
          <ContactForm
            initial={contactToFormValues(editingContact)}
            submitLabel={contactLabels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateContact}
          />
        </Modal>
      )}

      {modal === "create-activity" && (
        <Modal title={activityLabels.newActivity} onClose={closeModal} size="lg">
          <ActivityForm
            contacts={contactsForForm}
            submitLabel={activityLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateActivity}
          />
        </Modal>
      )}

      {modal === "edit-activity" && editingActivity && (
        <Modal title={activityLabels.editActivity} onClose={closeModal} size="lg">
          <ActivityForm
            contacts={contactsForForm}
            initial={activityToFormValues(editingActivity)}
            submitLabel={activityLabels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateActivity}
          />
        </Modal>
      )}

      {modal === "create-participation" && (
        <Modal title={participationLabels.newParticipation} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="customer"
            fairs={fairs}
            contacts={contactsForForm}
            submitLabel={participationLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateParticipation}
          />
        </Modal>
      )}

      {modal === "edit-participation" && editingParticipation && participationFormInitial && (
        <Modal title={participationLabels.editParticipation} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="customer"
            fairs={fairs}
            contacts={contactsForForm}
            initial={participationFormInitial}
            submitLabel={participationLabels.save}
            onCancel={closeModal}
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
          onCancel={closeConfirm}
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
          onCancel={closeConfirm}
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
          onCancel={closeConfirm}
          onConfirm={() => void handleDeleteParticipation(confirm.item)}
        />
      )}

      {confirm?.type === "archive" && (
        <ConfirmDialog
          title={labels.archive}
          message={labels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archiving}
          onCancel={closeConfirm}
          onConfirm={() => void handleArchiveCustomer()}
        />
      )}
    </div>
  );
}
