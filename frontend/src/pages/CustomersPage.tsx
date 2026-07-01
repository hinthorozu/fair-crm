import React from "react";
import {
  archiveCustomer,
  createCustomer,
  listCustomers,
  restoreCustomer,
  updateCustomer,
  ApiError,
  formatApiErrorMessage,
} from "../api/customers";
import { CustomerForm, customerToFormValues, type CustomerFormValues } from "../components/CustomerForm";
import { CustomerFilters, CustomerTable } from "../components/CustomerList";
import { PaginationBar } from "../components/Pagination";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState, TableSkeleton } from "../components/ui/LoadingState";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from "../types/pagination";
import { labels } from "../labels";

type ConfirmAction =
  | { type: "archive"; customer: Customer }
  | { type: "restore"; customer: Customer }
  | null;

export function CustomersPage({ onOpenDetail }: { onOpenDetail?: (customerId: string) => void }) {
  const [items, setItems] = React.useState<Customer[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<CustomerStatus | "">("");
  const [customerType, setCustomerType] = React.useState<CustomerType | "">("");
  const [page, setPage] = React.useState(DEFAULT_PAGE);
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Customer | null>(null);
  const [archivingId, setArchivingId] = React.useState<string | null>(null);
  const [restoringId, setRestoringId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);

  const load = React.useCallback(async (pageOverride?: number) => {
    const targetPage = pageOverride ?? page;
    setLoading(true);
    setError(null);
    try {
      const res = await listCustomers({
        search: search.trim() || undefined,
        status: status || undefined,
        customer_type: customerType || undefined,
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
      setError(err instanceof ApiError ? err.message : "Müşteriler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [search, status, customerType, page, pageSize]);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      void load();
    }, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const resetToFirstPage = () => setPage(DEFAULT_PAGE);

  const handleCreate = async (values: CustomerFormValues) => {
    await createCustomer(values);
    setModal(null);
    await load(DEFAULT_PAGE);
  };

  const handleUpdate = async (values: CustomerFormValues) => {
    if (!editing) return;
    await updateCustomer(editing.id, values);
    setModal(null);
    setEditing(null);
    await load();
  };

  const handleArchive = async (customer: Customer) => {
    setArchivingId(customer.id);
    setError(null);
    setSuccess(null);
    try {
      await archiveCustomer(customer.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Arşivleme başarısız.");
    } finally {
      setArchivingId(null);
      setConfirm(null);
    }
  };

  const handleRestore = async (customer: Customer) => {
    setRestoringId(customer.id);
    setError(null);
    setSuccess(null);
    try {
      await restoreCustomer(customer.id);
      setSuccess(labels.restoreSuccess);
      await load();
    } catch (err) {
      const fallback = "Arşivden çıkarma başarısız.";
      setError(
        err instanceof ApiError
          ? formatApiErrorMessage(err.status, err.message, fallback)
          : fallback,
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
        title={labels.customers}
        subtitle={`${total} kayıt`}
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            {labels.newCustomer}
          </button>
        }
      />

      <CustomerFilters
        search={search}
        status={status}
        customerType={customerType}
        onSearchChange={(value) => {
          resetToFirstPage();
          setSearch(value);
        }}
        onStatusChange={(value) => {
          setSuccess(null);
          resetToFirstPage();
          setStatus(value);
        }}
        onTypeChange={(value) => {
          resetToFirstPage();
          setCustomerType(value);
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
        <TableSkeleton rows={6} cols={6} />
      ) : (
        <CustomerTable
          items={items}
          archivingId={archivingId}
          restoringId={restoringId}
          onCreate={openCreate}
          onOpenDetail={onOpenDetail ? (c) => onOpenDetail(c.id) : undefined}
          onEdit={(c) => {
            setEditing(c);
            setModal("edit");
          }}
          onArchive={(c) => setConfirm({ type: "archive", customer: c })}
          onRestore={(c) => setConfirm({ type: "restore", customer: c })}
        />
      )}

      {modal === "create" && (
        <Modal title={labels.newCustomer} onClose={() => setModal(null)} size="lg">
          <CustomerForm
            submitLabel={labels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleCreate}
          />
        </Modal>
      )}

      {modal === "edit" && editing && (
        <Modal title={labels.editCustomer} onClose={() => setModal(null)} size="lg">
          <CustomerForm
            initial={customerToFormValues(editing)}
            submitLabel={labels.save}
            onCancel={() => setModal(null)}
            onSubmit={handleUpdate}
          />
        </Modal>
      )}

      {confirm?.type === "archive" && (
        <ConfirmDialog
          title={labels.archive}
          message={labels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archivingId === confirm.customer.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleArchive(confirm.customer)}
        />
      )}

      {confirm?.type === "restore" && (
        <ConfirmDialog
          title={labels.restore}
          message={labels.restoreConfirm}
          confirmLabel={labels.restore}
          loading={restoringId === confirm.customer.id}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void handleRestore(confirm.customer)}
        />
      )}
    </div>
  );
}
