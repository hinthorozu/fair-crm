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
import { FairForm, fairToFormValues, type FairFormValues } from "../components/FairForm";
import { FairFilters, FairTable } from "../components/FairList";
import { PaginationBar } from "../components/Pagination";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import { TableSkeleton } from "../components/ui/LoadingState";
import type { Fair, FairStatus } from "../types/fair";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";
import { fairLabels } from "../labels/fairLabels";
import { labels } from "../labels";

type ConfirmAction =
  | { type: "archive"; fair: Fair }
  | { type: "restore"; fair: Fair }
  | null;

interface FairsPageProps {
  onOpenDetail?: (fairId: string) => void;
}

export function FairsPage({ onOpenDetail }: FairsPageProps) {
  const [items, setItems] = React.useState<Fair[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<FairStatus | "">("");
  const [page, setPage] = React.useState(DEFAULT_PAGE);
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Fair | null>(null);
  const [archivingId, setArchivingId] = React.useState<string | null>(null);
  const [restoringId, setRestoringId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);

  const load = React.useCallback(async (pageOverride?: number) => {
    const targetPage = pageOverride ?? page;
    setLoading(true);
    setError(null);
    try {
      const res = await listFairs({
        search: search.trim() || undefined,
        status: status || undefined,
        page: targetPage,
        page_size: pageSize,
      });
      setItems(res.items);
      setPage(res.page);
      setPageSize(res.page_size);
      setTotal(res.total);
      setTotalPages(res.total_pages);
      if (pageOverride !== undefined && pageOverride !== res.page) {
        setPage(pageOverride);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.loadError);
    } finally {
      setLoading(false);
    }
  }, [search, status, page, pageSize]);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      void load();
    }, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const resetToFirstPage = () => setPage(DEFAULT_PAGE);

  const handleCreate = async (values: FairFormValues) => {
    await createFair(values);
    setModal(null);
    await load(DEFAULT_PAGE);
  };

  const handleUpdate = async (values: FairFormValues) => {
    if (!editing) return;
    await updateFair(editing.id, values);
    setModal(null);
    setEditing(null);
    await load();
  };

  const handleArchive = async (fair: Fair) => {
    setArchivingId(fair.id);
    setError(null);
    setSuccess(null);
    try {
      await archiveFair(fair.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.archiveError);
    } finally {
      setArchivingId(null);
      setConfirm(null);
    }
  };

  const handleRestore = async (fair: Fair) => {
    setRestoringId(fair.id);
    setError(null);
    setSuccess(null);
    try {
      await restoreFair(fair.id);
      setSuccess(fairLabels.restoreSuccess);
      await load();
    } catch (err) {
      setError(
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

  return (
    <div className="page">
      <PageHeader
        title={fairLabels.fairs}
        subtitle={`${total} kayıt`}
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            {fairLabels.newFair}
          </button>
        }
      />

      <FairFilters
        search={search}
        status={status}
        onSearchChange={(value) => {
          resetToFirstPage();
          setSearch(value);
        }}
        onStatusChange={(value) => {
          setSuccess(null);
          resetToFirstPage();
          setStatus(value);
        }}
        onRefresh={() => void load()}
      />

      {success && <div className="banner success">{success}</div>}
      {error && <div className="banner error">{error}</div>}

      <PaginationBar
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        loading={loading}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          resetToFirstPage();
          setPageSize(size);
        }}
      />

      {loading ? (
        <TableSkeleton rows={5} cols={7} />
      ) : (
        <FairTable
          items={items}
          archivingId={archivingId}
          restoringId={restoringId}
          onOpenDetail={onOpenDetail}
          onCreate={openCreate}
          onEdit={(f) => {
            setEditing(f);
            setModal("edit");
          }}
          onArchive={(f) => setConfirm({ type: "archive", fair: f })}
          onRestore={(f) => setConfirm({ type: "restore", fair: f })}
        />
      )}

      {modal === "create" && (
        <Modal title={fairLabels.newFair} onClose={() => setModal(null)} size="lg">
          <FairForm
            submitLabel={labels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreate}
          />
        </Modal>
      )}

      {modal === "edit" && editing && (
        <Modal title={fairLabels.editFair} onClose={() => setModal(null)} size="lg">
          <FairForm
            initial={fairToFormValues(editing)}
            submitLabel={labels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdate}
          />
        </Modal>
      )}

      {confirm?.type === "archive" && (
        <ConfirmDialog
          title={labels.archive}
          message={fairLabels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archivingId === confirm.fair.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleArchive(confirm.fair)}
        />
      )}

      {confirm?.type === "restore" && (
        <ConfirmDialog
          title={labels.restore}
          message={fairLabels.restoreConfirm}
          confirmLabel={labels.restore}
          loading={restoringId === confirm.fair.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleRestore(confirm.fair)}
        />
      )}
    </div>
  );
}
