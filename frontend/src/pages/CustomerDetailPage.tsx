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
import { getCustomer, archiveCustomer, updateCustomer } from "../api/customers";
import {
  createContact,
  deleteContact,
  listContactsByCustomer,
  updateContact,
} from "../api/contacts";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  ActivityForm,
  activityToFormValues,
  formValuesToUpdatePayload as activityFormValuesToUpdatePayload,
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
  formValuesToUpdatePayload as participationFormValuesToUpdatePayload,
  participationToFormValues,
  type ParticipationFormValues,
} from "../components/ParticipationForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { FormModal, TextInput } from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import {
  DetailEmailList,
  DetailPhoneList,
  DetailValue,
  DetailWebsite,
  DetailWebsiteList,
} from "../components/ui/DetailFields";
import { activityLabels } from "../labels/activityLabels";
import { contactLabels } from "../labels/contactLabels";
import { customerStatusLabels, customerTypeLabels, customerSourceLabels, labels } from "../labels";
import { participationLabels } from "../labels/participationLabels";
import { uiLabels } from "../labels/uiLabels";
import type { Activity } from "../types/activity";
import type { Customer } from "../types/customer";
import type { Contact } from "../types/contact";
import type { CustomerParticipationListItem } from "../types/participation";
import { customerStatusBadgeVariant } from "../utils/badges";
import {
  buildLocationSearch,
  navigateWithSearch,
  readSearchParams,
} from "../utils/urlState";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";
import { config } from "../config";
import { hasGrantedCorePermission } from "../permissions/corePermissions";

const PERMISSION_CUSTOMERS_UPDATE = "fair_crm.customers.update";
const PERMISSION_CUSTOMERS_DELETE = "fair_crm.customers.delete";
const PERMISSION_CONTACTS_READ = "fair_crm.contacts.read";
const PERMISSION_CONTACTS_CREATE = "fair_crm.contacts.create";
const PERMISSION_CONTACTS_UPDATE = "fair_crm.contacts.update";
const PERMISSION_CONTACTS_DELETE = "fair_crm.contacts.delete";
const PERMISSION_ACTIVITIES_READ = "fair_crm.activities.read";
const PERMISSION_ACTIVITIES_CREATE = "fair_crm.activities.create";
const PERMISSION_ACTIVITIES_UPDATE = "fair_crm.activities.update";
const PERMISSION_ACTIVITIES_DELETE = "fair_crm.activities.delete";
const PERMISSION_PARTICIPATIONS_READ = "fair_crm.participations.read";
const PERMISSION_PARTICIPATIONS_CREATE = "fair_crm.participations.create";
const PERMISSION_PARTICIPATIONS_UPDATE = "fair_crm.participations.update";
const PERMISSION_PARTICIPATIONS_DELETE = "fair_crm.participations.delete";

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
  const { session } = useAuth();
  const grantedPermissions = session?.permissions ?? [];
  const bypass = config.devBypassEnabled;
  const hasPermission = React.useCallback(
    (permissionCode: string) =>
      bypass || hasGrantedCorePermission(grantedPermissions, permissionCode),
    [bypass, grantedPermissions],
  );

  const canCustomerUpdate = hasPermission(PERMISSION_CUSTOMERS_UPDATE);
  const canCustomerDelete = hasPermission(PERMISSION_CUSTOMERS_DELETE);
  const canContactsRead = hasPermission(PERMISSION_CONTACTS_READ);
  const canContactsCreate = hasPermission(PERMISSION_CONTACTS_CREATE);
  const canContactsUpdate = hasPermission(PERMISSION_CONTACTS_UPDATE);
  const canContactsDelete = hasPermission(PERMISSION_CONTACTS_DELETE);
  const canActivitiesRead = hasPermission(PERMISSION_ACTIVITIES_READ);
  const canActivitiesCreate = hasPermission(PERMISSION_ACTIVITIES_CREATE);
  const canActivitiesUpdate = hasPermission(PERMISSION_ACTIVITIES_UPDATE);
  const canActivitiesDelete = hasPermission(PERMISSION_ACTIVITIES_DELETE);
  const canParticipationsRead = hasPermission(PERMISSION_PARTICIPATIONS_READ);
  const canParticipationsCreate = hasPermission(PERMISSION_PARTICIPATIONS_CREATE);
  const canParticipationsUpdate = hasPermission(PERMISSION_PARTICIPATIONS_UPDATE);
  const canParticipationsDelete = hasPermission(PERMISSION_PARTICIPATIONS_DELETE);

  const normalizeTab = React.useCallback(
    (tab: TabId): TabId => {
      if (tab === "contacts" && !canContactsRead) return "overview";
      if (tab === "activities" && !canActivitiesRead) return "overview";
      if (tab === "participations" && !canParticipationsRead) return "overview";
      return tab;
    },
    [canActivitiesRead, canContactsRead, canParticipationsRead],
  );

  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [contactsForForm, setContactsForForm] = React.useState<Contact[]>([]);
  const [activeTab, setActiveTabState] = React.useState<TabId>(() => normalizeTab(tabFromUrl()));
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
  const [createContactSessionKey, setCreateContactSessionKey] = React.useState(0);

  const closeModal = React.useCallback(() => setModal(null), []);
  const closeConfirm = React.useCallback(() => setConfirm(null), []);

  const detailPath = `/customers/${customerId}`;

  const contactsTable = useServerDataTable<Contact>({
    fetchFn: (params) => listContactsByCustomer(customerId, params),
    defaultSort: { field: "first_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: canContactsRead && activeTab === "contacts" && Boolean(customer),
  });

  const activitiesTable = useServerDataTable<Activity>({
    fetchFn: (params) => listActivitiesByCustomer(customerId, params),
    defaultSort: { field: "activity_date", direction: "desc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: canActivitiesRead && activeTab === "activities" && Boolean(customer),
  });

  const participationsTable = useServerDataTable<CustomerParticipationListItem>({
    fetchFn: (params) => listParticipationsByCustomer(customerId, params),
    defaultSort: { field: "fair_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: canParticipationsRead && activeTab === "participations" && Boolean(customer),
  });

  const setActiveTab = React.useCallback((tab: TabId) => {
    const nextTab = normalizeTab(tab);
    setActiveTabState(nextTab);
    const params = readSearchParams();
    if (nextTab === "overview") params.delete("tab");
    else params.set("tab", nextTab);
    navigateWithSearch(detailPath, buildLocationSearch(params));
  }, [detailPath, normalizeTab]);

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
    if (!canContactsRead) {
      setContactsForForm([]);
      return;
    }
    try {
      const res = await listContactsByCustomer(customerId, { page: 1, pageSize: 100 });
      setContactsForForm(res.items);
    } catch {
      // best-effort for form dropdown
    }
  }, [canContactsRead, customerId]);

  React.useEffect(() => {
    void loadCustomer();
  }, [loadCustomer]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(normalizeTab(tabFromUrl()));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [normalizeTab]);

  React.useEffect(() => {
    const normalized = normalizeTab(activeTab);
    if (normalized !== activeTab) setActiveTab(normalized);
  }, [activeTab, normalizeTab, setActiveTab]);

  React.useEffect(() => {
    if (!customer) return;
    if (canContactsRead) {
      void listContactsByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
        setContactsTotal(res.pagination.totalItems);
      });
    } else {
      setContactsTotal(0);
    }
    if (canActivitiesRead) {
      void listActivitiesByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
        setActivitiesTotal(res.pagination.totalItems);
      });
    } else {
      setActivitiesTotal(0);
    }
    if (canParticipationsRead) {
      void listParticipationsByCustomer(customerId, { page: 1, pageSize: 1 }).then((res) => {
        setParticipationsTotal(res.pagination.totalItems);
      });
    } else {
      setParticipationsTotal(0);
    }
  }, [
    canActivitiesRead,
    canContactsRead,
    canParticipationsRead,
    customerId,
    customer,
  ]);

  React.useEffect(() => {
    if (activeTab === "activities" && canActivitiesRead) {
      void loadContactsForForm();
    }
  }, [activeTab, canActivitiesRead, loadContactsForForm]);

  React.useEffect(() => {
    if (activeTab === "contacts" && canContactsRead) {
      setContactsTotal(contactsTable.pagination.totalItems);
    }
  }, [activeTab, canContactsRead, contactsTable.pagination.totalItems]);

  React.useEffect(() => {
    if (activeTab === "activities" && canActivitiesRead) {
      setActivitiesTotal(activitiesTable.pagination.totalItems);
    }
  }, [activeTab, activitiesTable.pagination.totalItems, canActivitiesRead]);

  React.useEffect(() => {
    if (activeTab === "participations" && canParticipationsRead) {
      setParticipationsTotal(participationsTable.pagination.totalItems);
    }
  }, [activeTab, canParticipationsRead, participationsTable.pagination.totalItems]);

  const handleCreateContact = async (values: ContactFormValues) => {
    if (!canContactsCreate) return;
    await createContact({ customer_id: customerId, ...values });
    setModal(null);
    if (canContactsRead) await contactsTable.refresh();
  };

  const handleCreateContactAndNew = async (values: ContactFormValues) => {
    if (!canContactsCreate) return;
    await createContact({ customer_id: customerId, ...values });
    setCreateContactSessionKey((key) => key + 1);
    if (canContactsRead) await contactsTable.refresh();
  };

  const handleUpdateContact = async (values: ContactFormValues) => {
    if (!canContactsUpdate || !editingContact) return;
    await updateContact(editingContact.id, values);
    setModal(null);
    setEditingContact(null);
    if (canContactsRead) await contactsTable.refresh();
  };

  const handleDeleteContact = async (contact: Contact) => {
    if (!canContactsDelete) return;
    setDeletingContactId(contact.id);
    setError(null);
    try {
      await deleteContact(contact.id);
      if (canContactsRead) await contactsTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : contactLabels.deleteError);
    } finally {
      setDeletingContactId(null);
      setConfirm(null);
    }
  };

  const handleCreateActivity = async (values: ActivityFormValues) => {
    if (!canActivitiesCreate) return;
    await createActivity({ customer_id: customerId, ...values });
    setModal(null);
    if (canActivitiesRead) await activitiesTable.refresh();
  };

  const handleUpdateActivity = async (values: ActivityFormValues) => {
    if (!canActivitiesUpdate || !editingActivity) return;
    await updateActivity(editingActivity.id, activityFormValuesToUpdatePayload(values));
    setModal(null);
    setEditingActivity(null);
    if (canActivitiesRead) await activitiesTable.refresh();
  };

  const handleDeleteActivity = async (activity: Activity) => {
    if (!canActivitiesDelete) return;
    setDeletingActivityId(activity.id);
    setError(null);
    try {
      await deleteActivity(activity.id);
      if (canActivitiesRead) await activitiesTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : activityLabels.deleteError);
    } finally {
      setDeletingActivityId(null);
      setConfirm(null);
    }
  };

  const handleCreateParticipation = async (values: ParticipationFormValues) => {
    if (!canParticipationsCreate) return;
    await createParticipation(formValuesToCreatePayload(values, "customer", customerId));
    setModal(null);
    if (canParticipationsRead) await participationsTable.refresh();
  };

  const handleUpdateParticipation = async (values: ParticipationFormValues) => {
    if (!canParticipationsUpdate || !editingParticipation) return;
    await updateParticipation(editingParticipation.id, participationFormValuesToUpdatePayload(values));
    setModal(null);
    setEditingParticipation(null);
    setParticipationFormInitial(undefined);
    if (canParticipationsRead) await participationsTable.refresh();
  };

  const handleDeleteParticipation = async (item: CustomerParticipationListItem) => {
    if (!canParticipationsDelete) return;
    setDeletingParticipationId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      if (canParticipationsRead) await participationsTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingParticipationId(null);
      setConfirm(null);
    }
  };

  const openEditParticipation = async (item: CustomerParticipationListItem) => {
    if (!canParticipationsRead || !canParticipationsUpdate) return;
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
    if (!canCustomerUpdate) return;
    await updateCustomer(customerId, values);
    setModal(null);
    await loadCustomer();
  };

  const handleArchiveCustomer = async () => {
    if (!canCustomerDelete) return;
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
    if (!canContactsCreate) return;
    setEditingContact(null);
    setModal("create-contact");
  };

  const openCreateActivity = () => {
    if (!canActivitiesCreate) return;
    void loadContactsForForm();
    setEditingActivity(null);
    setModal("create-activity");
  };

  const openCreateParticipation = () => {
    if (!canParticipationsCreate) return;
    setEditingParticipation(null);
    setParticipationFormInitial(undefined);
    setModal("create-participation");
  };

  const openCreateModal = () => {
    if (activeTab === "contacts" && canContactsCreate) {
      openCreateContact();
    } else if (activeTab === "activities" && canActivitiesCreate) {
      openCreateActivity();
    } else if (activeTab === "participations" && canParticipationsCreate) {
      openCreateParticipation();
    }
  };

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    ...(canContactsRead
      ? [
          {
            id: "contacts" as const,
            label: uiLabels.tabContacts,
            badge: contactsTotal > 0 ? contactsTotal : undefined,
          },
        ]
      : []),
    ...(canActivitiesRead
      ? [
          {
            id: "activities" as const,
            label: uiLabels.tabActivities,
            badge: activitiesTotal > 0 ? activitiesTotal : undefined,
          },
        ]
      : []),
    ...(canParticipationsRead
      ? [
          {
            id: "participations" as const,
            label: uiLabels.tabFairParticipations,
            badge: participationsTotal > 0 ? participationsTotal : undefined,
          },
        ]
      : []),
  ];

  if (loading) {
    return <LoadingState />;
  }

  if (!customer) {
    return (
      <PageShell>
        <Banner variant="error">{error ?? "Müşteri bulunamadı."}</Banner>
        <button type="button" className="btn secondary" onClick={onBack}>
          {contactLabels.backToCustomers}
        </button>
      </PageShell>
    );
  }

  const isArchived = customer.status === "archived" || customer.deleted_at !== null;

  const headerActions: PageHeaderAction[] = [];
  if (canCustomerUpdate) {
    headerActions.push({
      id: "edit",
      label: uiLabels.detailEdit,
      variant: "primary",
      onClick: () => setModal("edit-customer"),
      disabled: isArchived,
    });
  }
  if (canContactsCreate) {
    headerActions.push({
      id: "add-contact",
      label: uiLabels.detailAddContact,
      variant: "secondary",
      onClick: openCreateContact,
      disabled: isArchived,
    });
  }
  if (canParticipationsCreate) {
    headerActions.push({
      id: "add-participation",
      label: participationLabels.addToFair,
      variant: "secondary",
      onClick: openCreateParticipation,
      disabled: isArchived,
    });
  }
  if (canActivitiesCreate) {
    headerActions.push({
      id: "add-activity",
      label: uiLabels.detailNewActivity,
      variant: "secondary",
      onClick: openCreateActivity,
      disabled: isArchived,
    });
  }
  if (canCustomerDelete) {
    headerActions.push({
      id: "archive",
      label: labels.archive,
      variant: "danger",
      onClick: () => setConfirm({ type: "archive" }),
      disabled: isArchived,
      loading: archiving,
    });
  }

  return (
    <PageShell>
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

      {error && <Banner variant="error">{error}</Banner>}

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
            {customer.instagram_url ? (
              <div>
                <dt>{labels.instagram}</dt>
                <dd>
                  <DetailWebsite value={customer.instagram_url} />
                </dd>
              </div>
            ) : null}
            {customer.facebook_url ? (
              <div>
                <dt>{labels.facebook}</dt>
                <dd>
                  <DetailWebsite value={customer.facebook_url} />
                </dd>
              </div>
            ) : null}
            {customer.linkedin_url ? (
              <div>
                <dt>{labels.linkedin}</dt>
                <dd>
                  <DetailWebsite value={customer.linkedin_url} />
                </dd>
              </div>
            ) : null}
            {customer.youtube_url ? (
              <div>
                <dt>{labels.youtube}</dt>
                <dd>
                  <DetailWebsite value={customer.youtube_url} />
                </dd>
              </div>
            ) : null}
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

      {canContactsRead ? (
        <TabPanel id="panel-contacts" labelledBy="tab-contacts" active={activeTab === "contacts"}>
          <ServerDataTableFrame
            table={contactsTable}
            skeletonCols={6}
            toolbar={
              <FilterPanel
                actions={
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => void contactsTable.refresh()}
                  >
                    {labels.refresh}
                  </button>
                }
              >
                <TextInput
                  id="customer-contacts-search"
                  type="search"
                  className="search-input"
                  placeholder={uiLabels.searchContact}
                  value={contactsTable.search}
                  onChange={(e) => contactsTable.setSearch(e.target.value)}
                  aria-label={uiLabels.searchContact}
                />
              </FilterPanel>
            }
          >
            <ContactTable
              items={contactsTable.items}
              deletingId={deletingContactId}
              emptyDueToFilters={contactsTable.hasActiveFilters}
              sortField={contactsTable.sorting.field}
              sortDirection={contactsTable.sorting.direction}
              onSortChange={contactsTable.setSort}
              onCreate={canContactsCreate ? openCreateModal : undefined}
              onEdit={
                canContactsUpdate
                  ? (c) => {
                      setEditingContact(c);
                      setModal("edit-contact");
                    }
                  : undefined
              }
              onDelete={
                canContactsDelete ? (c) => setConfirm({ type: "contact", item: c }) : undefined
              }
            />
          </ServerDataTableFrame>
        </TabPanel>
      ) : null}

      {canActivitiesRead ? (
        <TabPanel id="panel-activities" labelledBy="tab-activities" active={activeTab === "activities"}>
          <ServerDataTableFrame
            table={activitiesTable}
            skeletonRows={4}
            toolbar={
              <FilterPanel
                actions={
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => void activitiesTable.refresh()}
                  >
                    {labels.refresh}
                  </button>
                }
              >
                <TextInput
                  id="customer-activities-search"
                  type="search"
                  className="search-input"
                  placeholder={uiLabels.searchActivity}
                  value={activitiesTable.search}
                  onChange={(e) => activitiesTable.setSearch(e.target.value)}
                  aria-label={uiLabels.searchActivity}
                />
              </FilterPanel>
            }
          >
            <ActivityTable
              items={activitiesTable.items}
              deletingId={deletingActivityId}
              emptyDueToFilters={activitiesTable.hasActiveFilters}
              sortField={activitiesTable.sorting.field}
              sortDirection={activitiesTable.sorting.direction}
              onSortChange={activitiesTable.setSort}
              onCreate={canActivitiesCreate ? openCreateModal : undefined}
              onEdit={
                canActivitiesUpdate
                  ? (a) => {
                      setEditingActivity(a);
                      setModal("edit-activity");
                    }
                  : undefined
              }
              onDelete={
                canActivitiesDelete ? (a) => setConfirm({ type: "activity", item: a }) : undefined
              }
            />
          </ServerDataTableFrame>
        </TabPanel>
      ) : null}

      {canParticipationsRead ? (
        <TabPanel
          id="panel-participations"
          labelledBy="tab-participations"
          active={activeTab === "participations"}
        >
          <ServerDataTableFrame
            table={participationsTable}
            skeletonCols={7}
            toolbar={
              <FilterPanel
                actions={
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => void participationsTable.refresh()}
                  >
                    {labels.refresh}
                  </button>
                }
              >
                <TextInput
                  id="customer-participations-search"
                  type="search"
                  className="search-input"
                  placeholder={uiLabels.searchFair}
                  value={participationsTable.search}
                  onChange={(e) => participationsTable.setSearch(e.target.value)}
                  aria-label={uiLabels.searchFair}
                />
              </FilterPanel>
            }
          >
            <CustomerParticipationTable
              items={participationsTable.items}
              deletingId={deletingParticipationId}
              emptyDueToFilters={participationsTable.hasActiveFilters}
              sortField={participationsTable.sorting.field}
              sortDirection={participationsTable.sorting.direction}
              onSortChange={participationsTable.setSort}
              onCreate={canParticipationsCreate ? openCreateModal : undefined}
              onEdit={canParticipationsUpdate ? (item) => void openEditParticipation(item) : undefined}
              onDelete={
                canParticipationsDelete
                  ? (item) => setConfirm({ type: "participation", item })
                  : undefined
              }
            />
          </ServerDataTableFrame>
        </TabPanel>
      ) : null}

      {modal === "edit-customer" && canCustomerUpdate && (
        <FormModal title={labels.editCustomer} onClose={closeModal} size="lg">
          <CustomerForm
            hydrateKey={customer.id}
            initial={customerToFormValues(customer)}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateCustomer}
          />
        </FormModal>
      )}

      {modal === "create-contact" && canContactsCreate && (
        <FormModal title={contactLabels.newContact} onClose={closeModal}>
          <ContactForm
            hydrateKey={`create-${createContactSessionKey}`}
            submitLabel={contactLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateContact}
            onSubmitAndNew={handleCreateContactAndNew}
            customerEmailAllowed={customer.email_allowed ?? true}
            customerSmsAllowed={customer.sms_allowed ?? true}
          />
        </FormModal>
      )}

      {modal === "edit-contact" && editingContact && canContactsUpdate && (
        <FormModal title={contactLabels.editContact} onClose={closeModal}>
          <ContactForm
            hydrateKey={editingContact.id}
            initial={contactToFormValues(editingContact)}
            submitLabel={contactLabels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateContact}
            customerEmailAllowed={customer.email_allowed ?? true}
            customerSmsAllowed={customer.sms_allowed ?? true}
          />
        </FormModal>
      )}

      {modal === "create-activity" && canActivitiesCreate && (
        <FormModal title={activityLabels.newActivity} onClose={closeModal}>
          <ActivityForm
            contacts={contactsForForm}
            submitLabel={activityLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateActivity}
          />
        </FormModal>
      )}

      {modal === "edit-activity" && editingActivity && canActivitiesUpdate && (
        <FormModal title={activityLabels.editActivity} onClose={closeModal}>
          <ActivityForm
            contacts={contactsForForm}
            hydrateKey={editingActivity.id}
            initial={activityToFormValues(editingActivity)}
            submitLabel={activityLabels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateActivity}
          />
        </FormModal>
      )}

      {modal === "create-participation" && canParticipationsCreate && (
        <FormModal title={participationLabels.newParticipation} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="customer"
            submitLabel={participationLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreateParticipation}
          />
        </FormModal>
      )}

      {modal === "edit-participation" &&
        editingParticipation &&
        participationFormInitial &&
        canParticipationsUpdate && (
          <FormModal title={participationLabels.editParticipation} onClose={closeModal} size="lg">
            <ParticipationForm
              mode="customer"
              hydrateKey={editingParticipation.id}
              initial={participationFormInitial}
              lockFair
              submitLabel={participationLabels.save}
              onCancel={closeModal}
              onSubmit={handleUpdateParticipation}
            />
          </FormModal>
        )}

      {confirm?.type === "contact" && canContactsDelete && (
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

      {confirm?.type === "activity" && canActivitiesDelete && (
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

      {confirm?.type === "participation" && canParticipationsDelete && (
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

      {confirm?.type === "archive" && canCustomerDelete && (
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
    </PageShell>
  );
}
