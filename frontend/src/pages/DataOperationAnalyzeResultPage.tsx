import React from "react";
import {
  assignCustomersToFair,
  deleteSelectedCustomers,
  exportDataOperationDatasetCustomers,
  getDataOperationRun,
  listDataOperationDatasetCustomers,
  ApiError,
} from "../api/dataOperations";
import { AssignCustomersToFairModal } from "../components/AssignCustomersToFairModal";
import { DeleteSelectedCustomersModal } from "../components/DeleteSelectedCustomersModal";
import { buildAnalysisCustomerColumns, CustomerFilters } from "../components/CustomerList";
import { PageHeader } from "../components/ui/PageHeader";
import { UniversalDataTable } from "../components/ui/UniversalDataTable";
import { EmptyState, EmptyStateIcon } from "../components/ui/EmptyState";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { useServerDataTableRowSelection } from "../hooks/useServerDataTableRowSelection";
import { adminLabels } from "../labels/adminLabels";
import { uiLabels } from "../labels/uiLabels";
import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import type { DataOperationRun } from "../types/dataOperations";
import { Card } from "../components/ui/Card";
import { PageShell } from "../components/ui/PageShell";

const POLL_INTERVAL_MS = 2000;

interface DataOperationAnalyzeResultPageProps {
  runId: string;
  onBack: () => void;
}

const analysisColumns = buildAnalysisCustomerColumns({
  companyName: adminLabels.dataOpColCompanyName,
  legalName: adminLabels.dataOpColLegalName,
  tradeName: adminLabels.dataOpColTradeName,
  customerType: adminLabels.dataOpColCustomerType,
  status: adminLabels.dataOpColStatusField,
  phone: adminLabels.dataOpColPhone,
  email: adminLabels.dataOpColEmail,
  website: adminLabels.dataOpColWebsite,
  city: adminLabels.dataOpColCity,
  country: adminLabels.dataOpColCountry,
  createdAt: adminLabels.dataOpColCreatedAt,
  updatedAt: adminLabels.dataOpColUpdatedAt,
});

function isRunInProgress(run: DataOperationRun | null): boolean {
  return run?.status === "queued" || run?.status === "running";
}

export function DataOperationAnalyzeResultPage({ runId, onBack }: DataOperationAnalyzeResultPageProps) {
  const [run, setRun] = React.useState<DataOperationRun | null>(null);
  const [runError, setRunError] = React.useState<string | null>(null);
  const [exporting, setExporting] = React.useState(false);
  const [assignModalOpen, setAssignModalOpen] = React.useState(false);
  const [assignFairId, setAssignFairId] = React.useState("");
  const [assignJobId, setAssignJobId] = React.useState<string | null>(null);
  const [assigning, setAssigning] = React.useState(false);
  const [assignMessage, setAssignMessage] = React.useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = React.useState(false);
  const [deleteJobId, setDeleteJobId] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteMessage, setDeleteMessage] = React.useState<string | null>(null);

  const actionBusy = assigning || deleting;

  const loadRun = React.useCallback(async () => {
    try {
      const next = await getDataOperationRun(runId);
      setRun(next);
      setRunError(null);
      return next;
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpLoadError);
      return null;
    }
  }, [runId]);

  React.useEffect(() => {
    void loadRun();
  }, [loadRun]);

  React.useEffect(() => {
    if (!isRunInProgress(run)) return undefined;

    const interval = window.setInterval(() => {
      void loadRun();
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(interval);
  }, [loadRun, run?.status]);

  const runReady = run?.result === "success";

  const table = useServerDataTable<Customer>({
    fetchFn: (params) =>
      listDataOperationDatasetCustomers(runId, {
        ...params,
        status: (params.filters.status as CustomerStatus | undefined) || undefined,
        customer_type: (params.filters.customer_type as CustomerType | undefined) || undefined,
        country: params.filters.country,
      }),
    defaultSort: { field: "name", direction: "asc" },
    filterKeys: ["status", "customer_type"],
    urlSync: true,
    urlPath: `/admin/data-operations/runs/${runId}`,
    enabled: runReady,
  });

  const summary = run?.summary_json;

  const pageRowIds = React.useMemo(() => table.items.map((customer) => customer.id), [table.items]);
  const rowSelection = useServerDataTableRowSelection(pageRowIds);
  const selectedCount = rowSelection.selectedIds.size;

  const pollAssignJob = React.useCallback(
    async (jobId: string) => {
      try {
        const job = await getDataOperationRun(jobId);
        if (job.status === "queued" || job.status === "running") {
          return;
        }
        if (job.status === "completed" && job.result === "success") {
          const jobSummary = job.summary_json ?? {};
          setAssignMessage(
            adminLabels.dataOpAssignToFairResult(
              Number(jobSummary.assigned_count ?? 0),
              Number(jobSummary.skipped_count ?? 0),
              Number(jobSummary.failed_count ?? 0),
            ),
          );
          rowSelection.clearSelection();
          await loadRun();
          await table.refresh();
        } else {
          setRunError(job.error_message ?? adminLabels.dataOpAssignToFairError);
        }
        setAssigning(false);
        setAssignJobId(null);
        setAssignModalOpen(false);
        setAssignFairId("");
      } catch (err) {
        setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpAssignToFairError);
        setAssigning(false);
        setAssignJobId(null);
      }
    },
    [loadRun, rowSelection, table.refresh],
  );

  React.useEffect(() => {
    if (!assignJobId) return undefined;
    const interval = window.setInterval(() => {
      void pollAssignJob(assignJobId);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [assignJobId, pollAssignJob]);

  const pollDeleteJob = React.useCallback(
    async (jobId: string) => {
      try {
        const job = await getDataOperationRun(jobId);
        if (job.status === "queued" || job.status === "running") {
          return;
        }
        if (job.status === "completed" && job.result === "success") {
          const jobSummary = job.summary_json ?? {};
          setDeleteMessage(
            adminLabels.dataOpDeleteSelectedResult(
              Number(jobSummary.deleted_count ?? 0),
              Number(jobSummary.skipped_count ?? 0),
              Number(jobSummary.failed_count ?? 0),
            ),
          );
          rowSelection.clearSelection();
          await loadRun();
          await table.refresh();
        } else {
          setRunError(job.error_message ?? adminLabels.dataOpDeleteSelectedError);
        }
        setDeleting(false);
        setDeleteJobId(null);
        setDeleteModalOpen(false);
      } catch (err) {
        setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpDeleteSelectedError);
        setDeleting(false);
        setDeleteJobId(null);
      }
    },
    [loadRun, rowSelection, table.refresh],
  );

  React.useEffect(() => {
    if (!deleteJobId) return undefined;
    const interval = window.setInterval(() => {
      void pollDeleteJob(deleteJobId);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [deleteJobId, pollDeleteJob]);

  const handleAssignToFair = async () => {
    if (!assignFairId || selectedCount === 0) return;
    setAssigning(true);
    setAssignMessage(null);
    setRunError(null);
    try {
      const response = await assignCustomersToFair(runId, {
        fair_id: assignFairId,
        customer_ids: Array.from(rowSelection.selectedIds),
      });
      setAssignJobId(response.id);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpAssignToFairError);
      setAssigning(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedCount === 0) return;
    setDeleting(true);
    setDeleteMessage(null);
    setRunError(null);
    try {
      const response = await deleteSelectedCustomers(runId, {
        customer_ids: Array.from(rowSelection.selectedIds),
      });
      setDeleteJobId(response.id);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpDeleteSelectedError);
      setDeleting(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportDataOperationDatasetCustomers(runId, {
        search: table.search,
        sortBy: table.sorting.field,
        sortOrder: table.sorting.direction,
        status: (table.filters.status as CustomerStatus | undefined) || undefined,
        customer_type: (table.filters.customer_type as CustomerType | undefined) || undefined,
        country: table.filters.country,
      });
      setRunError(null);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpExportError);
    } finally {
      setExporting(false);
    }
  };

  return (
    <PageShell className="data-operation-result-page">
      <PageHeader
        title={adminLabels.dataOpAnalyzeResultTitle}
        subtitle={adminLabels.dataOpAnalyzeResultSubtitle}
        actions={
          <button type="button" className="btn secondary" onClick={onBack}>
            {adminLabels.dataOpBackToOperations}
          </button>
        }
      />

      {runError && <p className="text-danger">{runError}</p>}
      {assignMessage && <p className="text-muted">{assignMessage}</p>}
      {deleteMessage && <p className="text-muted">{deleteMessage}</p>}
      {assigning && <p className="text-muted">{adminLabels.dataOpAssignToFairProgress}</p>}
      {deleting && <p className="text-muted">{adminLabels.dataOpDeleteSelectedProgress}</p>}

      {summary && (
        <div className="data-operation-summary-grid">
          <Card padding="none" className="data-operation-summary-card">
            <p className="data-operation-summary-label">{adminLabels.dataOpSummaryTotalCustomers}</p>
            <p className="data-operation-summary-value">{summary.total_customers ?? "—"}</p>
          </Card>
          <Card padding="none" className="data-operation-summary-card">
            <p className="data-operation-summary-label">{adminLabels.dataOpSummaryCustomersWithFair}</p>
            <p className="data-operation-summary-value">{summary.customers_with_fair ?? "—"}</p>
          </Card>
          <Card padding="none" className="data-operation-summary-card">
            <p className="data-operation-summary-label">{adminLabels.dataOpSummaryCustomersWithoutFair}</p>
            <p className="data-operation-summary-value">{summary.customers_without_fair ?? "—"}</p>
          </Card>
        </div>
      )}

      {isRunInProgress(run) && <p className="text-muted">{adminLabels.dataOpRunning}</p>}

      {run?.result === "failed" && (
        <p className="text-danger">{run.error_message ?? adminLabels.dataOpResultFailed}</p>
      )}

      {run && !runReady && !isRunInProgress(run) && run.result !== "failed" && !runError && (
        <p className="text-muted">{adminLabels.dataOpResultNotReady}</p>
      )}

      {runReady && (
        <UniversalDataTable
          table={table}
          columns={analysisColumns}
          rowKey={(customer) => customer.id}
          rowSelection={{
            controller: rowSelection,
            title: adminLabels.dataOpColSelection,
            selectAllAriaLabel: adminLabels.dataOpSelectAllOnPage,
            rowAriaLabel: (customer) => `Select ${customer.display_name}`,
          }}
          toolbar={
            <div className="data-operation-result-toolbar">
              <CustomerFilters
                search={table.search}
                status={(table.filters.status as CustomerStatus | "") ?? ""}
                customerType={(table.filters.customer_type as CustomerType | "") ?? ""}
                onSearchChange={table.setSearch}
                onStatusChange={(value) =>
                  table.setFilters({
                    ...table.filters,
                    status: value,
                    customer_type: table.filters.customer_type ?? "",
                  })
                }
                onTypeChange={(value) =>
                  table.setFilters({
                    ...table.filters,
                    customer_type: value,
                    status: table.filters.status ?? "",
                  })
                }
                onRefresh={() => void table.refresh()}
              />
              <button
                type="button"
                className="btn primary"
                disabled={selectedCount === 0 || actionBusy}
                onClick={() => setAssignModalOpen(true)}
              >
                {adminLabels.dataOpAssignToFair}
              </button>
              <button
                type="button"
                className="btn danger"
                disabled={selectedCount === 0 || actionBusy}
                onClick={() => setDeleteModalOpen(true)}
              >
                {adminLabels.dataOpDeleteSelected}
              </button>
              <button
                type="button"
                className="btn secondary"
                disabled={exporting || actionBusy}
                onClick={() => void handleExport()}
              >
                {exporting ? adminLabels.dataOpExporting : adminLabels.dataOpExportExcel}
              </button>
            </div>
          }
          emptyState={
            <EmptyState
              icon={<EmptyStateIcon />}
              title={table.hasActiveFilters ? uiLabels.emptySearchTitle : adminLabels.dataOpAnalyzeEmptyTitle}
              description={
                table.hasActiveFilters
                  ? uiLabels.emptySearchDescription
                  : adminLabels.dataOpAnalyzeEmptyDescription
              }
            />
          }
        />
      )}

      <AssignCustomersToFairModal
        open={assignModalOpen}
        selectedCount={selectedCount}
        fairId={assignFairId}
        assigning={assigning}
        onFairChange={setAssignFairId}
        onClose={() => {
          if (!assigning) {
            setAssignModalOpen(false);
            setAssignFairId("");
          }
        }}
        onAssign={() => void handleAssignToFair()}
      />

      <DeleteSelectedCustomersModal
        open={deleteModalOpen}
        selectedCount={selectedCount}
        deleting={deleting}
        onClose={() => {
          if (!deleting) {
            setDeleteModalOpen(false);
          }
        }}
        onConfirm={() => void handleDeleteSelected()}
      />
    </PageShell>
  );
}
