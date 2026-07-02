import React from "react";
import { getFair, archiveFair, updateFair } from "../api/fairs";
import {
  createParticipation,
  deleteParticipation,
  listParticipantsByFair,
  updateParticipation,
} from "../api/participations";
import { listCustomers } from "../api/customers";
import { ApiError } from "../api/client";
import { FairParticipantTable } from "../components/ParticipationList";
import {
  ParticipationForm,
  fairParticipantToFormValues,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
  type ParticipationFormValues,
} from "../components/ParticipationForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState } from "../components/ui/LoadingState";
import { Modal } from "../components/ui/Modal";
import { FairForm, fairToFormValues, type FairFormValues } from "../components/FairForm";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { participationLabels } from "../labels/participationLabels";
import { importLabels } from "../labels/importLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import type { Customer } from "../types/customer";
import type { Fair } from "../types/fair";
import type { FairParticipantListItem } from "../types/participation";
import { DEFAULT_PAGE } from "../types/listTable";
import {
  buildLocationSearch,
  navigateWithSearch,
  readSearchParams,
} from "../utils/urlState";

interface FairDetailPageProps {
  fairId: string;
  onBack: () => void;
  onFairLoaded?: (name: string) => void;
  onOpenCustomer?: (customerId: string) => void;
  onImportParticipants?: () => void;
}

type TabId = "overview" | "participants";

const VALID_TABS: TabId[] = ["overview", "participants"];

function tabFromUrl(): TabId {
  const tab = readSearchParams().get("tab");
  if (tab && VALID_TABS.includes(tab as TabId)) return tab as TabId;
  return "overview";
}

export function FairDetailPage({
  fairId,
  onBack,
  onFairLoaded,
  onOpenCustomer,
  onImportParticipants,
}: FairDetailPageProps) {
  const [fair, setFair] = React.useState<Fair | null>(null);
  const [customers, setCustomers] = React.useState<Customer[]>([]);
  const [activeTab, setActiveTabState] = React.useState<TabId>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"edit-fair" | "create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<FairParticipantListItem | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<FairParticipantListItem | null>(null);
  const [confirmArchive, setConfirmArchive] = React.useState(false);
  const [participantCount, setParticipantCount] = React.useState(0);

  const detailPath = `/fairs/${fairId}`;

  const participantsTable = useServerDataTable<FairParticipantListItem>({
    fetchFn: (params) => listParticipantsByFair(fairId, params),
    defaultSort: { field: "company_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: activeTab === "participants" && Boolean(fair),
  });

  const setActiveTab = React.useCallback(
    (tab: TabId) => {
      setActiveTabState(tab);
      const params = readSearchParams();
      if (tab === "overview") params.delete("tab");
      else params.set("tab", tab);
      navigateWithSearch(detailPath, buildLocationSearch(params));
    },
    [detailPath],
  );

  const loadFair = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFair(fairId);
      setFair(data);
      onFairLoaded?.(data.name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Fuar yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [fairId, onFairLoaded]);

  const loadCustomersForForm = React.useCallback(async () => {
    try {
      const res = await listCustomers({ page: 1, pageSize: 100, status: "active" });
      setCustomers(res.items);
    } catch {
      // best-effort
    }
  }, []);

  React.useEffect(() => {
    void loadFair();
  }, [loadFair]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  React.useEffect(() => {
    if (!fair) return;
    void listParticipantsByFair(fairId, { page: 1, pageSize: 1 }).then((res) => {
      setParticipantCount(res.pagination.totalItems);
    });
  }, [fairId, fair]);

  React.useEffect(() => {
    if (activeTab === "participants") {
      setParticipantCount(participantsTable.pagination.totalItems);
    }
  }, [activeTab, participantsTable.pagination.totalItems]);

  React.useEffect(() => {
    if (activeTab === "participants") {
      void loadCustomersForForm();
    }
  }, [activeTab, loadCustomersForForm]);

  const handleCreate = async (values: ParticipationFormValues) => {
    await createParticipation(formValuesToCreatePayload(values, "fair", fairId));
    setModal(null);
    await participantsTable.refresh();
  };

  const handleUpdate = async (values: ParticipationFormValues) => {
    if (!editing) return;
    await updateParticipation(editing.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditing(null);
    await participantsTable.refresh();
  };

  const handleDelete = async (item: FairParticipantListItem) => {
    setDeletingId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      await participantsTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingId(null);
      setConfirmDelete(null);
    }
  };

  const participantTotal = participantCount;

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    {
      id: "participants" as const,
      label: participationLabels.tabFairParticipants,
      badge: participantTotal > 0 ? participantTotal : undefined,
    },
  ];

  if (loading) {
    return <LoadingState />;
  }

  if (!fair) {
    return (
      <div className="page">
        <div className="banner error">{error ?? "Fuar bulunamadı."}</div>
        <button type="button" className="btn secondary" onClick={onBack}>
          ← {fairLabels.fairs}
        </button>
      </div>
    );
  }

  const handleUpdateFair = async (values: FairFormValues) => {
    await updateFair(fairId, values);
    setModal(null);
    await loadFair();
  };

  const handleArchiveFair = async () => {
    setArchiving(true);
    setError(null);
    try {
      await archiveFair(fairId);
      setConfirmArchive(false);
      onBack();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.archiveError);
    } finally {
      setArchiving(false);
    }
  };

  const openCreateParticipant = () => {
    void loadCustomersForForm();
    setEditing(null);
    setModal("create");
  };

  const isArchived = fair.status === "archived" || fair.deleted_at !== null;

  const headerActions: PageHeaderAction[] = [
    {
      id: "edit",
      label: uiLabels.detailEdit,
      variant: "primary",
      onClick: () => setModal("edit-fair"),
      disabled: isArchived,
    },
    {
      id: "add-participant",
      label: participationLabels.addCompany,
      variant: "secondary",
      onClick: openCreateParticipant,
      disabled: isArchived,
    },
    {
      id: "import",
      label: importLabels.importFromFair,
      variant: "secondary",
      onClick: () => onImportParticipants?.(),
      disabled: isArchived || !onImportParticipants,
    },
    {
      id: "activity",
      label: uiLabels.detailNewActivity,
      variant: "secondary",
      disabled: true,
      title: uiLabels.detailFairActivitySoon,
      onClick: () => undefined,
    },
    {
      id: "archive",
      label: labels.archive,
      variant: "danger",
      onClick: () => setConfirmArchive(true),
      disabled: isArchived,
      loading: archiving,
    },
  ];

  return (
    <div className="page">
      <PageHeader
        title={fair.name}
        subtitle={
          <Badge variant={fair.status === "archived" ? "danger" : "info"}>
            {fairStatusLabels[fair.status] ?? fair.status}
          </Badge>
        }
        breadcrumbs={[{ label: uiLabels.backToFairs, onClick: onBack }]}
        actions={headerActions}
      />

      <Tabs items={tabItems} active={activeTab} onChange={setActiveTab} />

      {error && <div className="banner error">{error}</div>}

      <TabPanel id="panel-fair-overview" labelledBy="tab-overview" active={activeTab === "overview"}>
        <Card>
          <dl className="detail-grid">
            <div>
              <dt>{fairLabels.name}</dt>
              <dd>{fair.name}</dd>
            </div>
            <div>
              <dt>{fairLabels.organizer}</dt>
              <dd>{fair.organizer ?? "—"}</dd>
            </div>
            <div>
              <dt>{fairLabels.venue}</dt>
              <dd>{fair.venue ?? "—"}</dd>
            </div>
            <div>
              <dt>{labels.city}</dt>
              <dd>{fair.city ?? "—"}</dd>
            </div>
            <div>
              <dt>{fairLabels.start_date}</dt>
              <dd>{fair.start_date ?? "—"}</dd>
            </div>
            <div>
              <dt>{fairLabels.end_date}</dt>
              <dd>{fair.end_date ?? "—"}</dd>
            </div>
            <div className="full-width">
              <dt>{labels.description}</dt>
              <dd>{fair.description ?? "—"}</dd>
            </div>
          </dl>
        </Card>
      </TabPanel>

      <TabPanel id="panel-participants" labelledBy="tab-participants" active={activeTab === "participants"}>
        <ServerDataTableFrame
          table={participantsTable}
          skeletonCols={8}
          toolbar={
            <div className="filters">
              <input
                type="search"
                className="search-input"
                placeholder={uiLabels.searchCustomer}
                value={participantsTable.search}
                onChange={(e) => participantsTable.setSearch(e.target.value)}
                aria-label={uiLabels.searchCustomer}
              />
              <button
                type="button"
                className="btn secondary"
                onClick={() => void participantsTable.refresh()}
              >
                {labels.refresh}
              </button>
            </div>
          }
        >
          <FairParticipantTable
            items={participantsTable.items}
            deletingId={deletingId}
            emptyDueToFilters={participantsTable.hasActiveFilters}
            sortField={participantsTable.sorting.field}
            sortDirection={participantsTable.sorting.direction}
            onSortChange={participantsTable.setSort}
            onCreate={openCreateParticipant}
            onEdit={(item) => {
              setEditing(item);
              setModal("edit");
            }}
            onDelete={(item) => setConfirmDelete(item)}
            onOpenCustomer={onOpenCustomer}
          />
        </ServerDataTableFrame>
      </TabPanel>

      {modal === "edit-fair" && (
        <Modal title={fairLabels.editFair} onClose={() => setModal(null)} size="lg">
          <FairForm
            initial={fairToFormValues(fair)}
            submitLabel={labels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdateFair}
          />
        </Modal>
      )}

      {modal === "create" && (
        <Modal title={participationLabels.newParticipant} onClose={() => setModal(null)} size="lg">
          <ParticipationForm
            mode="fair"
            customers={customers}
            submitLabel={participationLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreate}
          />
        </Modal>
      )}

      {modal === "edit" && editing && (
        <Modal title={participationLabels.editParticipant} onClose={() => setModal(null)} size="lg">
          <ParticipationForm
            mode="fair"
            customers={customers}
            initial={fairParticipantToFormValues(editing, editing.customer_id)}
            submitLabel={participationLabels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdate}
          />
        </Modal>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={uiLabels.delete}
          message={participationLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingId === confirmDelete.id}
          onCancel={() => setConfirmDelete(null)}
          onConfirm={() => void handleDelete(confirmDelete)}
        />
      )}

      {confirmArchive && (
        <ConfirmDialog
          title={labels.archive}
          message={fairLabels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archiving}
          onCancel={() => setConfirmArchive(false)}
          onConfirm={() => void handleArchiveFair()}
        />
      )}
    </div>
  );
}
