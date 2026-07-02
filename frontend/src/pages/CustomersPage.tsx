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
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import { useServerDataTable } from "../hooks/useServerDataTable";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { labels } from "../labels";

type ConfirmAction =
  | { type: "archive"; customer: Customer }
  | { type: "restore"; customer: Customer }
  | null;

export function CustomersPage({ onOpenDetail }: { onOpenDetail?: (customerId: string) => void }) {
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Customer | null>(null);
  const [archivingId, setArchivingId] = React.useState<string | null>(null);
  const [restoringId, setRestoringId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);

  const table = useServerDataTable<Customer>({
    fetchFn: (params) =>
      listCustomers({
        ...params,
        status: (params.filters.status as CustomerStatus | undefined) || undefined,
        customer_type: (params.filters.customer_type as CustomerType | undefined) || undefined,
        country: params.filters.country,
      }),
    defaultSort: { field: "name", direction: "asc" },
    filterKeys: ["status", "customer_type", "country"],
    urlSync: true,
    urlPath: "/customers",
  });

  const handleCreate = async (values: CustomerFormValues) => {
    await createCustomer(values);
    setModal(null);
    await table.refresh();
  };

  const handleUpdate = async (values: CustomerFormValues) => {
    if (!editing) return;
    await updateCustomer(editing.id, values);
    setModal(null);
    setEditing(null);
    await table.refresh();
  };

  const handleArchive = async (customer: Customer) => {
    setArchivingId(customer.id);
    try {
      await archiveCustomer(customer.id);
      await table.refresh();
    } catch (err) {
      // error surfaced via table refresh failure if needed
      console.error(err instanceof ApiError ? err.message : "Arşivleme başarısız.");
    } finally {
      setArchivingId(null);
      setConfirm(null);
    }
  };

  const handleRestore = async (customer: Customer) => {
    setRestoringId(customer.id);
    try {
      await restoreCustomer(customer.id);
      setSuccess(labels.restoreSuccess);
      await table.refresh();
    } catch (err) {
      console.error(
        err instanceof ApiError
          ? formatApiErrorMessage(err.status, err.message, "Arşivden çıkarma başarısız.")
          : "Arşivden çıkarma başarısız.",
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
        subtitle={`${table.pagination.totalItems} kayıt`}
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            {labels.newCustomer}
          </button>
        }
      />

      <ServerDataTableFrame
        table={table}
        toolbar={
          <CustomerFilters
            search={table.search}
            status={(table.filters.status as CustomerStatus | "") ?? ""}
            customerType={(table.filters.customer_type as CustomerType | "") ?? ""}
            onSearchChange={table.setSearch}
            onStatusChange={(value) => {
              setSuccess(null);
              table.setFilters({ ...table.filters, status: value, customer_type: table.filters.customer_type ?? "" });
            }}
            onTypeChange={(value) => {
              table.setFilters({ ...table.filters, customer_type: value, status: table.filters.status ?? "" });
            }}
            onRefresh={() => void table.refresh()}
          />
        }
      >
        <CustomerTable
          items={table.items}
          archivingId={archivingId}
          restoringId={restoringId}
          sortField={table.sorting.field}
          sortDirection={table.sorting.direction}
          onSortChange={table.setSort}
          emptyDueToFilters={table.hasActiveFilters}
          onCreate={openCreate}
          onOpenDetail={onOpenDetail ? (c) => onOpenDetail(c.id) : undefined}
          onEdit={(c) => {
            setEditing(c);
            setModal("edit");
          }}
          onArchive={(c) => setConfirm({ type: "archive", customer: c })}
          onRestore={(c) => setConfirm({ type: "restore", customer: c })}
        />
      </ServerDataTableFrame>

      {success && <div className="banner success">{success}</div>}

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
