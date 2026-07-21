import React from "react";
import {
  exportDataOperationDuplicateCustomers,
  getDataOperationDuplicateGroupDetail,
  getDataOperationRun,
  listDataOperationDuplicateGroups,
  ApiError,
} from "../api/dataOperations";
import { PaginationBar } from "../components/Pagination";
import { DuplicateGroupDetailView } from "../components/DuplicateGroupDetailView";
import { PageHeader } from "../components/ui/PageHeader";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { EmptyState, EmptyStateIcon } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { TextInput } from "../components/ui/form";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { adminLabels } from "../labels/adminLabels";
import { labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import type { DataOperationRun, DuplicateDatasetGroup } from "../types/dataOperations";
import { Banner } from "../components/ui/Banner";
import { Card } from "../components/ui/Card";
import { PageShell } from "../components/ui/PageShell";

const POLL_INTERVAL_MS = 2000;

interface DataOperationDuplicateResultPageProps {
  runId: string;
  onBack: () => void;
}

function isRunInProgress(run: DataOperationRun | null): boolean {
  return run?.status === "queued" || run?.status === "running";
}

function readGroupKeyFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get("group");
}

function writeGroupKeyToUrl(runId: string, groupKey: string | null) {
  const params = new URLSearchParams(window.location.search);
  if (groupKey) {
    params.set("group", groupKey);
  } else {
    params.delete("group");
  }
  const next = `/admin/data-operations/runs/${runId}?${params.toString()}`;
  if (`${window.location.pathname}${window.location.search}` !== next) {
    window.history.pushState(null, "", next);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }
}

function formatGroupByLabel(groupBy: string): string {
  if (groupBy === "company_name") return adminLabels.dataOpGroupByCompanyName;
  if (groupBy === "email") return adminLabels.dataOpGroupByEmail;
  if (groupBy === "website") return adminLabels.dataOpGroupByWebsite;
  if (groupBy === "phone") return adminLabels.dataOpGroupByPhone;
  return groupBy;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function formatSummaryNumber(value: string | number | undefined): string {
  if (value == null || value === "") return "—";
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toLocaleString("tr-TR");
}

function EllipsisText({ value, className }: { value: string; className?: string }) {
  return (
    <span
      className={["duplicate-groups-ellipsis", className].filter(Boolean).join(" ")}
      title={value}
    >
      {value}
    </span>
  );
}

function GroupKeyLink({ value, onOpen }: { value: string; onOpen: () => void }) {
  return (
    <button
      type="button"
      className="btn link duplicate-groups-key-link"
      onClick={onOpen}
      title={value}
      aria-label={value}
    >
      <span className="duplicate-groups-ellipsis">{value}</span>
    </button>
  );
}

function buildDuplicateGroupColumns(
  onOpenGroupDetail: (groupKey: string) => void,
): UniversalDataTableColumn<DuplicateDatasetGroup>[] {
  return [
    {
      key: "group_key",
      title: adminLabels.dataOpColGroupKey,
      sortable: true,
      className: "duplicate-groups-col-key",
      render: (row) => (
        <GroupKeyLink value={row.group_key} onOpen={() => onOpenGroupDetail(row.group_key)} />
      ),
    },
    {
      key: "group_by",
      title: adminLabels.dataOpColGroupBy,
      sortable: true,
      className: "duplicate-groups-col-group-by",
      render: (row) => formatGroupByLabel(row.group_by),
    },
    {
      key: "suggested_winner",
      title: adminLabels.dataOpColSuggestedWinner,
      sortable: true,
      className: "duplicate-groups-col-winner",
      sortField: "suggested_winner_company_name",
      render: (row) => <EllipsisText value={row.suggested_winner_company_name} />,
    },
    {
      key: "created_at_min",
      title: adminLabels.dataOpColCreatedAtMin,
      sortable: true,
      className: "duplicate-groups-col-date",
      render: (row) => formatDateTime(row.created_at_min),
    },
    {
      key: "created_at_max",
      title: adminLabels.dataOpColCreatedAtMax,
      sortable: true,
      className: "duplicate-groups-col-date",
      render: (row) => formatDateTime(row.created_at_max),
    },
  ];
}

export function DataOperationDuplicateResultPage({
  runId,
  onBack,
}: DataOperationDuplicateResultPageProps) {
  const [run, setRun] = React.useState<DataOperationRun | null>(null);
  const [runError, setRunError] = React.useState<string | null>(null);
  const [exporting, setExporting] = React.useState(false);
  const [selectedGroupKey, setSelectedGroupKey] = React.useState<string | null>(() =>
    readGroupKeyFromUrl(),
  );
  const [groupDetail, setGroupDetail] = React.useState<Awaited<
    ReturnType<typeof getDataOperationDuplicateGroupDetail>
  > | null>(null);
  const [groupDetailLoading, setGroupDetailLoading] = React.useState(false);
  const [groupDetailError, setGroupDetailError] = React.useState<string | null>(null);
  const [mergeSuccessMessage, setMergeSuccessMessage] = React.useState<string | null>(null);
  const [analysisResultsStale, setAnalysisResultsStale] = React.useState(false);

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

  React.useEffect(() => {
    const onPopState = () => {
      setSelectedGroupKey(readGroupKeyFromUrl());
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  React.useEffect(() => {
    if (!selectedGroupKey) {
      setGroupDetail(null);
      setGroupDetailError(null);
      return;
    }

    let cancelled = false;
    setGroupDetail(null);
    setGroupDetailLoading(true);
    setGroupDetailError(null);
    void (async () => {
      try {
        const detail = await getDataOperationDuplicateGroupDetail(runId, selectedGroupKey);
        if (!cancelled) {
          setGroupDetail(detail);
        }
      } catch (err) {
        if (!cancelled) {
          setGroupDetailError(err instanceof ApiError ? err.message : adminLabels.dataOpLoadError);
          setGroupDetail(null);
        }
      } finally {
        if (!cancelled) {
          setGroupDetailLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [runId, selectedGroupKey]);

  const runReady = run?.result === "success";

  const table = useServerDataTable<DuplicateDatasetGroup>({
    fetchFn: (params) => listDataOperationDuplicateGroups(runId, params),
    defaultSort: { field: "group_key", direction: "asc" },
    filterKeys: [],
    urlSync: !selectedGroupKey,
    urlPath: `/admin/data-operations/runs/${runId}`,
    enabled: runReady && !selectedGroupKey,
  });

  const summary = run?.summary_json;
  const liveDuplicateGroupCount =
    typeof table.filters.liveDuplicateGroups === "number"
      ? table.filters.liveDuplicateGroups
      : table.pagination.totalItems;
  const liveCustomersInDuplicateGroups =
    typeof table.filters.liveCustomersInDuplicateGroups === "number"
      ? table.filters.liveCustomersInDuplicateGroups
      : summary?.customers_in_duplicate_groups;

  const refreshDuplicateGroups = React.useCallback(() => {
    void table.refresh();
    void loadRun();
  }, [loadRun, table.refresh]);

  React.useEffect(() => {
    if (!runReady || selectedGroupKey) return;
    const onPageShow = () => refreshDuplicateGroups();
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, [runReady, selectedGroupKey, refreshDuplicateGroups]);

  const openGroupDetail = (groupKey: string) => {
    writeGroupKeyToUrl(runId, groupKey);
    setSelectedGroupKey(groupKey);
  };

  const closeGroupDetail = () => {
    writeGroupKeyToUrl(runId, null);
    setSelectedGroupKey(null);
  };

  const handleMergeSuccess = React.useCallback(
    (_payload: { groupKey: string }) => {
      writeGroupKeyToUrl(runId, null);
      setSelectedGroupKey(null);
      setMergeSuccessMessage(adminLabels.dataOpMergeSuccess);
      setAnalysisResultsStale(true);
      refreshDuplicateGroups();
    },
    [runId, refreshDuplicateGroups],
  );

  React.useEffect(() => {
    if (!mergeSuccessMessage) return undefined;
    const timer = window.setTimeout(() => setMergeSuccessMessage(null), 5000);
    return () => window.clearTimeout(timer);
  }, [mergeSuccessMessage]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportDataOperationDuplicateCustomers(runId, {
        search: table.search,
        sortBy: table.sorting.field,
        sortOrder: table.sorting.direction,
      });
      setRunError(null);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : adminLabels.dataOpExportError);
    } finally {
      setExporting(false);
    }
  };

  const groupColumns = buildDuplicateGroupColumns(openGroupDetail);

  const showingGroupsList = runReady && !selectedGroupKey;

  const showStaleAnalysisNotice =
    showingGroupsList &&
    (analysisResultsStale ||
      (!table.loading &&
        summary?.duplicate_groups != null &&
        liveDuplicateGroupCount !== Number(summary.duplicate_groups)));

  return (
    <PageShell className={`data-operation-result-page${showingGroupsList ? " duplicate-groups-page" : ""}`}>
      <PageHeader
        title={
          selectedGroupKey
            ? adminLabels.dataOpDuplicateGroupDetailTitle
            : adminLabels.dataOpDuplicateGroupsTitle
        }
        subtitle={
          selectedGroupKey
            ? adminLabels.dataOpDuplicateGroupDetailSubtitle
            : adminLabels.dataOpDuplicateGroupsSubtitle
        }
        actions={
          selectedGroupKey ? (
            <div className="page-header-action-group">
              <button type="button" className="btn secondary" onClick={closeGroupDetail}>
                {adminLabels.dataOpBackToDuplicateGroups}
              </button>
              <button type="button" className="btn secondary" onClick={onBack}>
                {adminLabels.dataOpBackToOperations}
              </button>
            </div>
          ) : (
            <button type="button" className="btn secondary" onClick={onBack}>
              {adminLabels.dataOpBackToOperations}
            </button>
          )
        }
      />

      {runError && <p className="text-danger">{runError}</p>}

      {mergeSuccessMessage && showingGroupsList && (
        <Banner variant="success" className="duplicate-groups-merge-success" role="status">
          {mergeSuccessMessage}
        </Banner>
      )}

      {showStaleAnalysisNotice && (
        <Banner variant="info" className="duplicate-groups-stale-notice" role="status">
          {adminLabels.dataOpDuplicateAnalysisStale}
        </Banner>
      )}

      {showingGroupsList && summary && (
        <div className="duplicate-groups-summary-grid">
          <Card padding="none" className="duplicate-groups-summary-card">
            <p className="duplicate-groups-summary-label">{adminLabels.dataOpSummaryGroupBy}</p>
            <p className="duplicate-groups-summary-value">
              {summary.group_by ? formatGroupByLabel(String(summary.group_by)) : "—"}
            </p>
          </Card>
          <Card padding="none" className="duplicate-groups-summary-card">
            <p className="duplicate-groups-summary-label">{adminLabels.dataOpSummaryTotalCustomers}</p>
            <p className="duplicate-groups-summary-value">
              {formatSummaryNumber(summary.total_customers)}
            </p>
          </Card>
          <Card padding="none" className="duplicate-groups-summary-card">
            <p className="duplicate-groups-summary-label">{adminLabels.dataOpSummaryDuplicateGroups}</p>
            <p className="duplicate-groups-summary-value">
              {formatSummaryNumber(
                showingGroupsList && !table.loading
                  ? liveDuplicateGroupCount
                  : summary?.duplicate_groups,
              )}
            </p>
          </Card>
          <Card padding="none" className="duplicate-groups-summary-card">
            <p className="duplicate-groups-summary-label">
              {adminLabels.dataOpSummaryCustomersInDuplicateGroups}
            </p>
            <p className="duplicate-groups-summary-value">
              {formatSummaryNumber(
                showingGroupsList && !table.loading
                  ? liveCustomersInDuplicateGroups
                  : summary?.customers_in_duplicate_groups,
              )}
            </p>
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

      {runReady && selectedGroupKey && (
        <DuplicateGroupDetailView
          runId={runId}
          groupKey={selectedGroupKey}
          groupBy={groupDetail?.group_by}
          customers={
            groupDetail?.group_key === selectedGroupKey ? groupDetail.customers : []
          }
          loading={groupDetailLoading || groupDetail?.group_key !== selectedGroupKey}
          error={groupDetailError}
          onMergeSuccess={handleMergeSuccess}
        />
      )}

      {showingGroupsList && (
        <UniversalDataTable
          className="duplicate-groups-table"
          table={table}
          columns={groupColumns}
          rowKey={(row) => row.group_key}
          showPagination={false}
          toolbar={
            <div className="duplicate-groups-toolbar-stack">
              <FilterPanel
                actions={
                  <>
                    <button type="button" className="btn secondary" onClick={() => void table.refresh()}>
                      {labels.refresh}
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={exporting}
                      onClick={() => void handleExport()}
                    >
                      {exporting ? adminLabels.dataOpExporting : adminLabels.dataOpExportExcel}
                    </button>
                  </>
                }
              >
                <TextInput
                  id="duplicate-groups-search"
                  type="search"
                  className="search-input"
                  placeholder={adminLabels.dataOpDuplicateGroupsSearchPlaceholder}
                  value={table.search}
                  onChange={(e) => table.setSearch(e.target.value)}
                  aria-label={adminLabels.dataOpDuplicateGroupsSearchPlaceholder}
                />
              </FilterPanel>
              <PaginationBar
                className="duplicate-groups-pagination"
                page={table.pagination.page}
                pageSize={table.pagination.pageSize}
                total={table.pagination.totalItems}
                totalPages={table.pagination.totalPages}
                loading={table.loading}
                onPageChange={table.setPage}
                onPageSizeChange={table.setPageSize}
              />
            </div>
          }
          emptyState={
            <EmptyState
              icon={<EmptyStateIcon />}
              title={table.hasActiveFilters ? uiLabels.emptySearchTitle : adminLabels.dataOpDuplicateEmptyTitle}
              description={
                table.hasActiveFilters
                  ? uiLabels.emptySearchDescription
                  : adminLabels.dataOpDuplicateEmptyDescription
              }
            />
          }
        />
      )}
    </PageShell>
  );
}
