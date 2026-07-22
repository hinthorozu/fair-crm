import React from "react";
import {
  deleteScraperRun,
  downloadScraperRunOutput,
  listAdapters,
  listScraperRunsTable,
} from "../api/scraper";
import { ApiError } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/Badge";
import { FilterPanel } from "../components/ui/FilterPanel";
import { FormField, SelectInput, TextInput } from "../components/ui/form";
import { TruncatedText } from "../components/ui/TruncatedText";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { TableRowActions } from "../components/ui/TableRowActions";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { scraperLabels } from "../labels/scraperLabels";
import type { AdapterListItem, ScraperRun, ScraperRunStatus } from "../types/scraper";
import { runStatusBadgeVariant, runStatusLabel } from "../utils/scraperBadges";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";

interface ScraperRunHistoryPageProps {
  initialAdapterKey?: string;
  onOpenAdapter?: (adapterKey: string) => void;
  onOpenRunDetail?: (adapterKey: string, runId: string) => void;
  onOpenImportBatch?: (batchId: string) => void;
}

function runSourceLabel(value: ScraperRun["run_source"]): string {
  if (value === "fair_automation") return scraperLabels.runSourceFairAutomation;
  if (value === "manual_test") return scraperLabels.runSourceManualTest;
  if (value === "enrichment") return scraperLabels.runSourceEnrichment;
  return "—";
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function formatDurationMs(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value < 1000) return `${value} ms`;
  const seconds = Math.round(value / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest > 0 ? `${minutes}m ${rest}s` : `${minutes}m`;
}

function engineTypeLabel(value: string | null | undefined): string {
  if (value === "static") return scraperLabels.runEngineTypeStatic;
  if (value === "dynamic") return scraperLabels.runEngineTypeDynamic;
  return value ?? "—";
}

function isActiveRunStatus(status: ScraperRunStatus): boolean {
  return status === "running" || status === "cancel_requested" || status === "cancelling";
}

function RunHistoryFilesMenu({
  run,
  onDownload,
  loadingKey,
}: {
  run: ScraperRun;
  onDownload: (run: ScraperRun, kind: "json" | "excel") => void;
  loadingKey: string | null;
}) {
  const hasJson = Boolean(run.output_json_available);
  const hasExcel = Boolean(run.output_excel_available);
  const [open, setOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDocumentClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, [open]);

  if (!hasJson && !hasExcel) {
    return <span className="text-muted">—</span>;
  }

  const loading = Boolean(loadingKey?.startsWith(`${run.id}:`));

  const handleDownload = (event: React.MouseEvent, kind: "json" | "excel") => {
    event.preventDefault();
    event.stopPropagation();
    setOpen(false);
    onDownload(run, kind);
  };

  return (
    <div className="run-history-files-menu" ref={menuRef}>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={loading}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      >
        {scraperLabels.runColFiles}
      </button>
      {open ? (
        <div className="run-history-files-dropdown" role="menu">
          {hasJson ? (
            <button
              type="button"
              role="menuitem"
              className="run-history-files-item"
              disabled={loadingKey === `${run.id}:json`}
              onClick={(event) => handleDownload(event, "json")}
            >
              {scraperLabels.testOutputJsonDownload}
            </button>
          ) : null}
          {hasExcel ? (
            <button
              type="button"
              role="menuitem"
              className="run-history-files-item"
              disabled={loadingKey === `${run.id}:excel`}
              onClick={(event) => handleDownload(event, "excel")}
            >
              {scraperLabels.testOutputExcelDownload}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function buildColumns(
  handlers: {
    onOpenAdapter?: (adapterKey: string) => void;
    onOpenRunDetail?: (adapterKey: string, runId: string) => void;
    onOpenImportBatch?: (batchId: string) => void;
    onDownload: (run: ScraperRun, kind: "json" | "excel") => void;
    onDelete: (run: ScraperRun) => void;
    loadingKey: string | null;
    deletingRunId: string | null;
  },
): UniversalDataTableColumn<ScraperRun>[] {
  return [
    {
      key: "started_at",
      title: scraperLabels.runColStarted,
      sortable: false,
      priority: "primary",
      render: (run) => formatDateTime(run.started_at),
    },
    {
      key: "status",
      title: scraperLabels.runColStatus,
      sortable: false,
      priority: "primary",
      render: (run) => (
        <Badge variant={runStatusBadgeVariant(run.status)}>{runStatusLabel(run.status)}</Badge>
      ),
    },
    {
      key: "actions",
      title: scraperLabels.runColDetail,
      sortable: false,
      priority: "primary",
      className: "actions",
      render: (run) => (
        <TableRowActions className="run-history-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            onClick={() => handlers.onOpenRunDetail?.(run.adapter_key, run.id)}
          >
            {scraperLabels.actionDetail}
          </button>
          <button
            type="button"
            className="btn btn-sm danger"
            disabled={isActiveRunStatus(run.status) || handlers.deletingRunId === run.id}
            onClick={() => handlers.onDelete(run)}
          >
            {handlers.deletingRunId === run.id ? "Siliniyor…" : scraperLabels.runHistoryDelete}
          </button>
        </TableRowActions>
      ),
    },
    {
      key: "adapter_name",
      title: scraperLabels.runColAdapterName,
      sortable: false,
      priority: "primary",
      render: (run) =>
        handlers.onOpenAdapter ? (
          <button type="button" className="btn link" onClick={() => handlers.onOpenAdapter?.(run.adapter_key)}>
            {run.adapter_name ?? run.adapter_key}
          </button>
        ) : (
          run.adapter_name ?? run.adapter_key
        ),
    },
    {
      key: "fair_name",
      title: scraperLabels.runColFairName,
      sortable: false,
      priority: "primary",
      render: (run) => run.fair_name ?? "—",
    },
    {
      key: "total_rows",
      title: scraperLabels.runColRows,
      sortable: false,
      priority: "primary",
      render: (run) => run.total_rows.toLocaleString("tr-TR"),
    },
    {
      key: "run_source",
      title: scraperLabels.runColSource,
      sortable: false,
      priority: "secondary",
      render: (run) => runSourceLabel(run.run_source),
    },
    {
      key: "engine_type",
      title: scraperLabels.runColEngineType,
      sortable: false,
      priority: "secondary",
      render: (run) => engineTypeLabel(run.engine_type),
    },
    {
      key: "duration_ms",
      title: scraperLabels.runColDuration,
      sortable: false,
      priority: "secondary",
      render: (run) => formatDurationMs(run.duration_ms),
    },
    {
      key: "files",
      title: scraperLabels.runColFiles,
      sortable: false,
      priority: "secondary",
      render: (run) => (
        <RunHistoryFilesMenu run={run} onDownload={handlers.onDownload} loadingKey={handlers.loadingKey} />
      ),
    },
    {
      key: "import_batch_id",
      title: scraperLabels.runColImportBatch,
      sortable: false,
      priority: "secondary",
      render: (run) =>
        run.import_batch_id && handlers.onOpenImportBatch ? (
          <button
            type="button"
            className="btn link"
            onClick={() => handlers.onOpenImportBatch?.(run.import_batch_id!)}
          >
            {scraperLabels.actionOpenImport}
          </button>
        ) : (
          <span className="text-muted">—</span>
        ),
    },
    {
      key: "adapter_key",
      title: scraperLabels.runColAdapterKey,
      sortable: false,
      priority: "technical",
      render: (run) => <TruncatedText value={run.adapter_key} mono maxLength={28} />,
    },
    {
      key: "engine_key",
      title: scraperLabels.runColEngineKey,
      sortable: false,
      priority: "technical",
      render: (run) => <TruncatedText value={run.engine_key} mono maxLength={28} />,
    },
    {
      key: "input_url",
      title: scraperLabels.runColInputUrl,
      sortable: false,
      priority: "technical",
      render: (run) =>
        run.input_url ? (
          <a href={run.input_url} target="_blank" rel="noreferrer" className="run-history-url text-wrap">
            <TruncatedText value={run.input_url} maxLength={48} />
          </a>
        ) : (
          "—"
        ),
    },
    {
      key: "run_id",
      title: "Run ID",
      sortable: false,
      priority: "technical",
      render: (run) => <TruncatedText value={run.id} mono maxLength={12} />,
    },
  ];
}

const POLL_INTERVAL_MS = 12_000;

export function ScraperRunHistoryPage({
  initialAdapterKey,
  onOpenAdapter,
  onOpenRunDetail,
  onOpenImportBatch,
}: ScraperRunHistoryPageProps) {
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [outputLoading, setOutputLoading] = React.useState<string | null>(null);
  const [outputError, setOutputError] = React.useState<string | null>(null);
  const [runToDelete, setRunToDelete] = React.useState<ScraperRun | null>(null);
  const [deletingRunId, setDeletingRunId] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);
  const silentRefreshInFlight = React.useRef(false);
  const loadingRef = React.useRef(false);

  const table = useServerDataTable<ScraperRun>({
    fetchFn: listScraperRunsTable,
    defaultSort: { field: "started_at", direction: "desc" },
    defaultFilters: initialAdapterKey ? { adapter_key: initialAdapterKey } : {},
    filterKeys: ["adapter_key", "status", "engine_type", "date_from", "date_to", "url"],
    urlSync: true,
    urlPath: "/data-integration/run-history",
  });

  loadingRef.current = table.loading;

  const hasActiveRuns = table.items.some((run) => isActiveRunStatus(run.status));

  const silentRefresh = React.useCallback(async () => {
    if (silentRefreshInFlight.current || loadingRef.current) return;
    silentRefreshInFlight.current = true;
    try {
      await table.refresh({ silent: true });
    } finally {
      silentRefreshInFlight.current = false;
    }
  }, [table.refresh]);

  React.useEffect(() => {
    void listAdapters()
      .then((response) => setAdapters(response.items))
      .catch(() => setAdapters([]));
  }, []);

  React.useEffect(() => {
    if (!hasActiveRuns) return;
    const interval = window.setInterval(() => {
      void silentRefresh();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [hasActiveRuns, silentRefresh]);

  React.useEffect(() => {
    if (!successMessage) return;
    const timer = window.setTimeout(() => setSuccessMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [successMessage]);

  const handleManualRefresh = React.useCallback(() => {
    void silentRefresh();
  }, [silentRefresh]);

  const handleDownload = React.useCallback(async (run: ScraperRun, kind: "json" | "excel") => {
    const key = `${run.id}:${kind}`;
    setOutputLoading(key);
    setOutputError(null);
    try {
      await downloadScraperRunOutput(run.id, kind, `${run.id}.${kind === "json" ? "json" : "xlsx"}`);
    } catch (err) {
      setOutputError(err instanceof ApiError ? err.message : scraperLabels.testOutputDownloadError);
    } finally {
      setOutputLoading(null);
    }
  }, []);

  const handleConfirmDelete = React.useCallback(async () => {
    if (!runToDelete) return;
    setDeletingRunId(runToDelete.id);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await deleteScraperRun(runToDelete.id);
      setRunToDelete(null);
      setSuccessMessage(scraperLabels.runHistoryDeleteSuccess);
      await table.refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : scraperLabels.runHistoryDeleteError);
    } finally {
      setDeletingRunId(null);
    }
  }, [runToDelete, table]);

  const columns = React.useMemo(
    () =>
      buildColumns({
        onOpenAdapter,
        onOpenRunDetail,
        onOpenImportBatch,
        onDownload: (run, kind) => void handleDownload(run, kind),
        onDelete: setRunToDelete,
        loadingKey: outputLoading,
        deletingRunId,
      }),
    [handleDownload, onOpenAdapter, onOpenRunDetail, onOpenImportBatch, outputLoading, deletingRunId],
  );

  const statusOptions: ScraperRunStatus[] = ["running", "completed", "failed", "cancelled"];
  const showEmpty = !table.loading && !table.error && table.items.length === 0;
  const bannerError = actionError ?? outputError;

  const filtersToolbar = (
    <FilterPanel className="run-history-filters">
      <FormField label={scraperLabels.runFilterAdapter} htmlFor="run-filter-adapter">
        <SelectInput
          id="run-filter-adapter"
          value={table.filters.adapter_key ?? ""}
          onChange={(event) => table.setFilter("adapter_key", event.target.value)}
        >
          <option value="">{scraperLabels.runFilterAll}</option>
          {adapters.map((adapter) => (
            <option key={adapter.adapter_key} value={adapter.adapter_key}>
              {adapter.display_name}
            </option>
          ))}
        </SelectInput>
      </FormField>
      <FormField label={scraperLabels.runFilterStatus} htmlFor="run-filter-status">
        <SelectInput
          id="run-filter-status"
          value={table.filters.status ?? ""}
          onChange={(event) => table.setFilter("status", event.target.value)}
        >
          <option value="">{scraperLabels.runFilterAll}</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {runStatusLabel(status)}
            </option>
          ))}
        </SelectInput>
      </FormField>
      <FormField label={scraperLabels.runFilterEngineType} htmlFor="run-filter-engine-type">
        <SelectInput
          id="run-filter-engine-type"
          value={table.filters.engine_type ?? ""}
          onChange={(event) => table.setFilter("engine_type", event.target.value)}
        >
          <option value="">{scraperLabels.runFilterAll}</option>
          <option value="static">{scraperLabels.runEngineTypeStatic}</option>
          <option value="dynamic">{scraperLabels.runEngineTypeDynamic}</option>
        </SelectInput>
      </FormField>
      <FormField label={scraperLabels.runFilterDateFrom} htmlFor="run-filter-date-from">
        <TextInput
          id="run-filter-date-from"
          type="date"
          value={table.filters.date_from ?? ""}
          onChange={(event) => table.setFilter("date_from", event.target.value)}
        />
      </FormField>
      <FormField label={scraperLabels.runFilterDateTo} htmlFor="run-filter-date-to">
        <TextInput
          id="run-filter-date-to"
          type="date"
          value={table.filters.date_to ?? ""}
          onChange={(event) => table.setFilter("date_to", event.target.value)}
        />
      </FormField>
      <div className="run-history-url-filter">
        <FormField label={scraperLabels.runFilterUrl} htmlFor="run-filter-url" fullWidth>
          <TextInput
            id="run-filter-url"
            type="search"
            value={table.search}
            placeholder="https://"
            onChange={(event) => table.setSearch(event.target.value)}
          />
        </FormField>
      </div>
    </FilterPanel>
  );

  return (
    <PageShell className="scraper-run-history-page">
      <PageHeader
        title={scraperLabels.runHistoryTitle}
        subtitle={scraperLabels.runHistorySubtitle}
        actions={[
          {
            id: "refresh-run-history",
            label: scraperLabels.runHistoryRefresh,
            onClick: handleManualRefresh,
            variant: "secondary",
            disabled: table.loading || table.isRefreshing,
          },
        ]}
      />

      {successMessage ? <Banner variant="success">{successMessage}</Banner> : null}
      {bannerError ? <Banner variant="error">{bannerError}</Banner> : null}

      <UniversalDataTable
        table={table}
        toolbar={filtersToolbar}
        skeletonCols={8}
        columns={columns}
        rowKey={(run) => run.id}
        className="scraper-run-history-table"
        emptyState={showEmpty ? <EmptyState title={scraperLabels.runHistoryEmpty} /> : undefined}
      />

      {runToDelete ? (
        <ConfirmDialog
          title={scraperLabels.runHistoryDeleteTitle}
          message={scraperLabels.buildDeleteRunHistoryMessage(runToDelete)}
          confirmLabel={scraperLabels.runHistoryDeleteConfirmLabel}
          variant="danger"
          loading={deletingRunId === runToDelete.id}
          onCancel={() => {
            if (deletingRunId) return;
            setRunToDelete(null);
          }}
          onConfirm={() => void handleConfirmDelete()}
        />
      ) : null}
    </PageShell>
  );
}
