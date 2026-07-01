import React from "react";
import { getFair } from "../api/fairs";
import {
  createParticipation,
  deleteParticipation,
  listParticipantsByFair,
  updateParticipation,
} from "../api/participations";
import { listCustomers } from "../api/customers";
import { ApiError } from "../api/client";
import {
  FairParticipantTable,
} from "../components/ParticipationList";
import {
  ParticipationForm,
  fairParticipantToFormValues,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
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
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { participationLabels } from "../labels/participationLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import type { Customer } from "../types/customer";
import type { Fair } from "../types/fair";
import type { FairParticipantListItem } from "../types/participation";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";

interface FairDetailPageProps {
  fairId: string;
  onBack: () => void;
  onFairLoaded?: (name: string) => void;
  onOpenCustomer?: (customerId: string) => void;
}

type TabId = "overview" | "participants";

export function FairDetailPage({
  fairId,
  onBack,
  onFairLoaded,
  onOpenCustomer,
}: FairDetailPageProps) {
  const [fair, setFair] = React.useState<Fair | null>(null);
  const [participants, setParticipants] = React.useState<FairParticipantListItem[]>([]);
  const [customers, setCustomers] = React.useState<Customer[]>([]);
  const [activeTab, setActiveTab] = React.useState<TabId>("overview");
  const [loading, setLoading] = React.useState(true);
  const [participantsLoading, setParticipantsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [page, setPage] = React.useState(DEFAULT_PAGE);
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<FairParticipantListItem | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = React.useState<FairParticipantListItem | null>(null);

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

  const loadParticipants = React.useCallback(async () => {
    setParticipantsLoading(true);
    try {
      const res = await listParticipantsByFair(fairId, { page, page_size: pageSize });
      setParticipants(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.loadError);
    } finally {
      setParticipantsLoading(false);
    }
  }, [fairId, page, pageSize]);

  const loadCustomersForForm = React.useCallback(async () => {
    try {
      const res = await listCustomers({ page: 1, page_size: 100, status: "active" });
      setCustomers(res.items);
    } catch {
      // best-effort
    }
  }, []);

  React.useEffect(() => {
    void loadFair();
  }, [loadFair]);

  React.useEffect(() => {
    if (!fair) return;
    void listParticipantsByFair(fairId, { page: 1, page_size: 1 }).then((res) => {
      setTotal(res.total);
    });
  }, [fairId, fair]);

  React.useEffect(() => {
    if (activeTab === "participants") {
      void loadParticipants();
      void loadCustomersForForm();
    }
  }, [activeTab, loadParticipants, loadCustomersForForm]);

  const handleCreate = async (values: ParticipationFormValues) => {
    await createParticipation(formValuesToCreatePayload(values, "fair", fairId));
    setModal(null);
    setPage(DEFAULT_PAGE);
    await loadParticipants();
  };

  const handleUpdate = async (values: ParticipationFormValues) => {
    if (!editing) return;
    await updateParticipation(editing.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditing(null);
    await loadParticipants();
  };

  const handleDelete = async (item: FairParticipantListItem) => {
    setDeletingId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      await loadParticipants();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingId(null);
      setConfirmDelete(null);
    }
  };

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    {
      id: "participants" as const,
      label: participationLabels.tabFairParticipants,
      badge: total > 0 ? total : undefined,
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

  return (
    <div className="page">
      <PageHeader
        title={fair.name}
        subtitle={
          <Badge variant={fair.status === "archived" ? "danger" : "info"}>
            {fairStatusLabels[fair.status] ?? fair.status}
          </Badge>
        }
        backAction={
          <button type="button" className="btn link back-link" onClick={onBack}>
            ← {fairLabels.fairs}
          </button>
        }
        actions={
          activeTab === "participants" ? (
            <button
              type="button"
              className="btn primary"
              onClick={() => {
                setEditing(null);
                setModal("create");
              }}
            >
              {participationLabels.addCompany}
            </button>
          ) : undefined
        }
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
        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          totalPages={totalPages}
          loading={participantsLoading}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPage(DEFAULT_PAGE);
            setPageSize(size);
          }}
        />
        {participantsLoading ? (
          <TableSkeleton rows={4} cols={8} />
        ) : (
          <FairParticipantTable
            items={participants}
            deletingId={deletingId}
            onCreate={() => setModal("create")}
            onEdit={(item) => {
              setEditing(item);
              setModal("edit");
            }}
            onDelete={(item) => setConfirmDelete(item)}
            onOpenCustomer={onOpenCustomer}
          />
        )}
      </TabPanel>

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
    </div>
  );
}
