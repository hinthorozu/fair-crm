import React from "react";
import {
  archiveCustomer,
  createCustomer,
  exportCustomers,
  listCustomers,
  restoreCustomer,
  updateCustomer,
  ApiError,
  formatApiErrorMessage,
} from "../api/customers";
import { CustomerForm, customerToFormValues } from "../components/CustomerForm";
import type { CreateCustomerPayload } from "../types/customer";
import {
  CustomerFilters,
  CustomerTable,
  type CustomerMissingInfoFilter,
} from "../components/CustomerList";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FormModal, runAfterSuccessfulFormSubmit } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { usePermissions } from "../hooks/usePermissions";
import { useServerDataTable } from "../hooks/useServerDataTable";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { labels } from "../labels";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";
import {
  CUSTOMER_CREATE,
  CUSTOMER_DELETE,
  CUSTOMER_EXECUTE,
  CUSTOMER_UPDATE,
} from "../permissions/customerPermissions";

type ConfirmAction =
  | { type: "archive"; customer: Customer }
  | { type: "restore"; customer: Customer }
  | null;

export function CustomersPage({ onOpenDetail }: { onOpenDetail?: (customerId: string) => void }) {
  const { can } = usePermissions();
  const canCreate = can(CUSTOMER_CREATE);
  const canUpdate = can(CUSTOMER_UPDATE);
  const canDelete = can(CUSTOMER_DELETE);
  const canExecute = can(CUSTOMER_EXECUTE);

  const [success, setSuccess] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Customer | null>(null);
  const [archivingId, setArchivingId] = React.useState<string | null>(null);
  const [restoringId, setRestoringId] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState<ConfirmAction>(null);
  const [createSessionKey, setCreateSessionKey] = React.useState(0);
  const [exporting, setExporting] = React.useState(false);

  const table = useServerDataTable<Customer>({
    fetchFn: (params) =>
      listCustomers({
        ...params,
        status: (params.filters.status as CustomerStatus | undefined) || undefined,
        customer_type: (params.filters.customer_type as CustomerType | undefined) || undefined,
        country: params.filters.country,
        missing_info: params.filters.missing_info || undefined,
      }),
    defaultSort: { field: "name", direction: "asc" },
    filterKeys: ["status", "customer_type", "country", "missing_info"],
    urlSync: true,
    urlPath: "/customers",
  });

  const handleCreate = async (values: CreateCustomerPayload) => {
    const created = await createCustomer(values);
    if (onOpenDetail) {
      runAfterSuccessfulFormSubmit(() => {
        setModal(null);
        onOpenDetail(created.id);
      });
      return;
    }
    runAfterSuccessfulFormSubmit(() => setModal(null));
    await table.refresh();
  };

  const handleCreateAndNew = async (values: CreateCustomerPayload) => {
    await createCustomer(values);
    setCreateSessionKey((key) => key + 1);
    await table.refresh();
  };

  const handleUpdate = async (values: CreateCustomerPayload) => {
    if (!editing) return;
    const updated = await updateCustomer(editing.id, values);
    if (onOpenDetail) {
      runAfterSuccessfulFormSubmit(() => {
        setModal(null);
        setEditing(null);
        onOpenDetail(updated.id);
      });
      return;
    }
    runAfterSuccessfulFormSubmit(() => {
      setModal(null);
      setEditing(null);
    });
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

  const handleExport = async () => {
    if (!canExecute) return;
    setExporting(true);
    setError(null);
    try {
      await exportCustomers({
        // Use the same search that produced pagination.totalItems (post-debounce).
        search: table.appliedSearch,
        sortBy: table.sorting.field,
        sortOrder: table.sorting.direction,
        status: (table.filters.status as CustomerStatus | undefined) || undefined,
        customer_type: (table.filters.customer_type as CustomerType | undefined) || undefined,
        country: table.filters.country,
        missing_info: table.filters.missing_info || undefined,
        filters: {
          ...(table.filters.status ? { status: table.filters.status } : {}),
          ...(table.filters.customer_type
            ? { customer_type: table.filters.customer_type }
            : {}),
          ...(table.filters.country ? { country: table.filters.country } : {}),
          ...(table.filters.missing_info
            ? { missing_info: table.filters.missing_info }
            : {}),
        },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : labels.excelExportError);
    } finally {
      setExporting(false);
    }
  };

  const openCreate = () => {
    if (!canCreate) return;
    setEditing(null);
    setModal("create");
  };

  const closeModal = React.useCallback(() => setModal(null), []);
  const closeConfirm = React.useCallback(() => setConfirm(null), []);

  return (
    <PageShell>
      <PageHeader
        title={labels.customers}
        subtitle={`${table.pagination.totalItems} kayıt`}
        actions={
          canCreate ? (
            <button type="button" className="btn primary" onClick={openCreate}>
              {labels.newCustomer}
            </button>
          ) : undefined
        }
      />

      <ServerDataTableFrame
        table={table}
        toolbar={
          <CustomerFilters
            search={table.search}
            status={(table.filters.status as CustomerStatus | "") ?? ""}
            customerType={(table.filters.customer_type as CustomerType | "") ?? ""}
            missingInfo={(table.filters.missing_info as CustomerMissingInfoFilter | undefined) ?? ""}
            onSearchChange={table.setSearch}
            onStatusChange={(value) => {
              setSuccess(null);
              table.setFilters({
                ...table.filters,
                status: value,
                customer_type: table.filters.customer_type ?? "",
                missing_info: table.filters.missing_info ?? "",
              });
            }}
            onTypeChange={(value) => {
              table.setFilters({
                ...table.filters,
                customer_type: value,
                status: table.filters.status ?? "",
                missing_info: table.filters.missing_info ?? "",
              });
            }}
            onMissingInfoChange={(value) => {
              table.setFilters({
                ...table.filters,
                missing_info: value,
                status: table.filters.status ?? "",
                customer_type: table.filters.customer_type ?? "",
              });
            }}
            onRefresh={() => void table.refresh()}
            onExport={canExecute ? () => void handleExport() : undefined}
            exporting={exporting}
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
          onCreate={canCreate ? openCreate : undefined}
          onOpenDetail={onOpenDetail ? (c) => onOpenDetail(c.id) : undefined}
          onEdit={
            canUpdate
              ? (c) => {
                  setEditing(c);
                  setModal("edit");
                }
              : undefined
          }
          onArchive={
            canDelete ? (c) => setConfirm({ type: "archive", customer: c }) : undefined
          }
          onRestore={
            canDelete ? (c) => setConfirm({ type: "restore", customer: c }) : undefined
          }
        />
      </ServerDataTableFrame>

      {success && <Banner variant="success">{success}</Banner>}
      {error && (
        <Banner variant="error" role="alert">
          {error}
        </Banner>
      )}

      {modal === "create" && canCreate && (
        <FormModal title={labels.newCustomer} onClose={closeModal} size="lg">
          <CustomerForm
            hydrateKey={`create-${createSessionKey}`}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleCreate}
            onSubmitAndNew={handleCreateAndNew}
          />
        </FormModal>
      )}

      {modal === "edit" && editing && canUpdate && (
        <FormModal title={labels.editCustomer} onClose={closeModal} size="lg">
          <CustomerForm
            hydrateKey={editing.id}
            initial={customerToFormValues(editing)}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleUpdate}
          />
        </FormModal>
      )}

      {confirm?.type === "archive" && canDelete && (
        <ConfirmDialog
          title={labels.archive}
          message={labels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archivingId === confirm.customer.id}
          onCancel={closeConfirm}
          onConfirm={() => void handleArchive(confirm.customer)}
        />
      )}

      {confirm?.type === "restore" && canDelete && (
        <ConfirmDialog
          title={labels.restore}
          message={labels.restoreConfirm}
          confirmLabel={labels.restore}
          loading={restoringId === confirm.customer.id}
          onCancel={closeConfirm}
          onConfirm={() => void handleRestore(confirm.customer)}
        />
      )}
    </PageShell>
  );
}
