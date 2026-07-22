import React from "react";
import {
  archiveFair,
  createFair,
  listFairs,
  restoreFair,
  updateFair,
  ApiError,
  formatApiErrorMessage,
} from "../api/fairs";
import { FairForm, fairToFormValues } from "../components/FairForm";
import { FairFilters, FairTable } from "../components/FairList";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { useServerDataTable } from "../hooks/useServerDataTable";
import type { CreateFairPayload, Fair, FairStatus } from "../types/fair";
import { fairLabels } from "../labels/fairLabels";
import { labels } from "../labels";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";

type ConfirmAction =
  | { type: "archive"; fair: Fair }
  | { type: "restore"; fair: Fair }
  | null;

interface FairsPageProps {
  onOpenDetail?: (fairId: string) => void;
}

export function FairsPage({ onOpenDetail }: FairsPageProps) {
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Fair | null>(null);
  const [archivingId, setArchivingId] = React.useState<string | null>(null);
  const [restoringId, setRestoringId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);

  const table = useServerDataTable<Fair>({
    fetchFn: (params) =>
      listFairs({
        ...params,
        status: (params.filters.status as FairStatus | undefined) || undefined,
      }),
    defaultSort: { field: "start_date", direction: "desc" },
    filterKeys: ["status"],
    urlSync: true,
    urlPath: "/fairs",
  });

  const handleCreate = async (values: CreateFairPayload) => {
    await createFair(values);
    setModal(null);
    await table.refresh();
  };

  const handleUpdate = async (values: CreateFairPayload) => {
    if (!editing) return;
    await updateFair(editing.id, values);
    setModal(null);
    setEditing(null);
    await table.refresh();
  };

  const handleArchive = async (fair: Fair) => {
    setArchivingId(fair.id);
    setSuccess(null);
    try {
      await archiveFair(fair.id);
      await table.refresh();
    } catch (err) {
      console.error(err instanceof ApiError ? err.message : fairLabels.archiveError);
    } finally {
      setArchivingId(null);
      setConfirm(null);
    }
  };

  const handleRestore = async (fair: Fair) => {
    setRestoringId(fair.id);
    setSuccess(null);
    try {
      await restoreFair(fair.id);
      setSuccess(fairLabels.restoreSuccess);
      await table.refresh();
    } catch (err) {
      console.error(
        err instanceof ApiError
          ? formatApiErrorMessage(err.status, err.message, fairLabels.restoreError)
          : fairLabels.restoreError,
      );
    } finally {
      setRestoringId(null);
      setConfirm(null);
    }
  };

  const openCreate = () => {
    setEditing(null);
    setModal("create");
  };

  const closeModal = React.useCallback(() => setModal(null), []);
  const closeConfirm = React.useCallback(() => setConfirm(null), []);

  return (
    <PageShell>
      <PageHeader
        title={fairLabels.fairs}
        subtitle={`${table.pagination.totalItems} kayıt`}
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            {fairLabels.newFair}
          </button>
        }
      />

      <ServerDataTableFrame
        table={table}
        skeletonCols={7}
        toolbar={
          <FairFilters
            search={table.search}
            status={(table.filters.status as FairStatus | "") ?? ""}
            onSearchChange={table.setSearch}
            onStatusChange={(value) => {
              setSuccess(null);
              table.setFilters({ ...table.filters, status: value });
            }}
            onRefresh={() => void table.refresh()}
          />
        }
      >
        <FairTable
          items={table.items}
          archivingId={archivingId}
          restoringId={restoringId}
          sortField={table.sorting.field}
          sortDirection={table.sorting.direction}
          onSortChange={table.setSort}
          emptyDueToFilters={table.hasActiveFilters}
          onOpenDetail={onOpenDetail}
          onCreate={openCreate}
          onEdit={(f) => {
            setEditing(f);
            setModal("edit");
          }}
          onArchive={(f) => setConfirm({ type: "archive", fair: f })}
          onRestore={(f) => setConfirm({ type: "restore", fair: f })}
        />
      </ServerDataTableFrame>

      {success && <Banner variant="success">{success}</Banner>}

      {modal === "create" && (
        <FormModal title={fairLabels.newFair} onClose={closeModal} size="lg">
          <FairForm
            key="create-fair"
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleCreate}
          />
        </FormModal>
      )}

      {modal === "edit" && editing && (
        <FormModal title={fairLabels.editFair} onClose={closeModal} size="lg">
          <FairForm
            key={editing.id}
            initial={fairToFormValues(editing)}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleUpdate}
          />
        </FormModal>
      )}

      {confirm?.type === "archive" && (
        <ConfirmDialog
          title={labels.archive}
          message={fairLabels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archivingId === confirm.fair.id}
          onCancel={closeConfirm}
          onConfirm={() => void handleArchive(confirm.fair)}
        />
      )}

      {confirm?.type === "restore" && (
        <ConfirmDialog
          title={labels.restore}
          message={fairLabels.restoreConfirm}
          confirmLabel={labels.restore}
          loading={restoringId === confirm.fair.id}
          onCancel={closeConfirm}
          onConfirm={() => void handleRestore(confirm.fair)}
        />
      )}
    </PageShell>
  );
}
