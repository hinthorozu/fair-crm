import React from "react";
import { downloadScraperRunOutput, listAdapters, listScraperRunsTable } from "../api/scraper";
import { ApiError } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { scraperLabels } from "../labels/scraperLabels";
import type { AdapterListItem, ScraperRun, ScraperRunStatus } from "../types/scraper";
import { runStatusBadgeVariant, runStatusLabel } from "../utils/scraperBadges";

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
    loadingKey: string | null;
  },
): UniversalDataTableColumn<ScraperRun>[] {
  return [
    {
      key: "started_at",
      title: scraperLabels.runColStarted,
      sortable: false,
      render: (run) => formatDateTime(run.started_at),
    },
    {
      key: "run_source",
      title: scraperLabels.runColSource,
      sortable: false,
      render: (run) => runSourceLabel(run.run_source),
    },
    {
      key: "fair_name",
      title: scraperLabels.runColFairName,
      sortable: false,
      render: (run) => run.fair_name ?? "—",
    },
    {
      key: "adapter_name",
      title: scraperLabels.runColAdapterName,
      sortable: false,
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
      key: "adapter_key",
      title: scraperLabels.runColAdapterKey,
      sortable: false,
      render: (run) => run.adapter_key,
    },
    {
      key: "engine_key",
      title: scraperLabels.runColEngineKey,
      sortable: false,
      render: (run) => run.engine_key ?? "—",
    },
    {
      key: "engine_type",
      title: scraperLabels.runColEngineType,
      sortable: false,
      render: (run) => engineTypeLabel(run.engine_type),
    },
    {
      key: "input_url",
      title: scraperLabels.runColInputUrl,
      sortable: false,
      render: (run) =>
        run.input_url ? (
          <a href={run.input_url} target="_blank" rel="noreferrer" className="run-history-url">
            {run.input_url}
          </a>
        ) : (
          "—"
        ),
    },
    {
      key: "status",
      title: scraperLabels.runColStatus,
      sortable: false,
      render: (run) => (
        <Badge variant={runStatusBadgeVariant(run.status)}>{runStatusLabel(run.status)}</Badge>
      ),
    },
    {
      key: "total_rows",
      title: scraperLabels.runColRows,
      sortable: false,
      render: (run) => run.total_rows.toLocaleString("tr-TR"),
    },
    {
      key: "duration_ms",
      title: scraperLabels.runColDuration,
      sortable: false,
      render: (run) => formatDurationMs(run.duration_ms),
    },
    {
      key: "files",
      title: scraperLabels.runColFiles,
      sortable: false,
      render: (run) => (
        <RunHistoryFilesMenu run={run} onDownload={handlers.onDownload} loadingKey={handlers.loadingKey} />
      ),
    },
    {
      key: "import_batch_id",
      title: scraperLabels.runColImportBatch,
      sortable: false,
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
      key: "detail",
      title: scraperLabels.runColDetail,
      sortable: false,
      render: (run) => (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => handlers.onOpenRunDetail?.(run.adapter_key, run.id)}
        >
          {scraperLabels.actionDetail}
        </button>
      ),
    },
  ];
}

export function ScraperRunHistoryPage({
  initialAdapterKey,
  onOpenAdapter,
  onOpenRunDetail,
  onOpenImportBatch,
}: ScraperRunHistoryPageProps) {
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [outputLoading, setOutputLoading] = React.useState<string | null>(null);
  const [outputError, setOutputError] = React.useState<string | null>(null);

  const table = useServerDataTable<ScraperRun>({
    fetchFn: listScraperRunsTable,
    defaultSort: { field: "started_at", direction: "desc" },
    defaultFilters: initialAdapterKey ? { adapter_key: initialAdapterKey } : {},
    filterKeys: ["adapter_key", "status", "engine_type", "date_from", "date_to", "url"],
    urlSync: true,
    urlPath: "/data-integration/run-history",
  });

  React.useEffect(() => {
    void listAdapters()
      .then((response) => setAdapters(response.items))
      .catch(() => setAdapters([]));
  }, []);

  React.useEffect(() => {
    const hasRunning = table.items.some((run) => run.status === "running");
    if (!hasRunning) {
      return;
    }
    const interval = window.setInterval(() => {
      void table.refresh();
    }, 3000);
    return () => window.clearInterval(interval);
  }, [table.items, table.refresh]);

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

  const columns = React.useMemo(
    () =>
      buildColumns({
        onOpenAdapter,
        onOpenRunDetail,
        onOpenImportBatch,
        onDownload: (run, kind) => void handleDownload(run, kind),
        loadingKey: outputLoading,
      }),
    [handleDownload, onOpenAdapter, onOpenRunDetail, onOpenImportBatch, outputLoading],
  );

  const statusOptions: ScraperRunStatus[] = ["running", "completed", "failed", "cancelled"];

  return (
    <div className="page scraper-run-history-page">
      <PageHeader
        title={scraperLabels.runHistoryTitle}
        subtitle={scraperLabels.runHistorySubtitle}
      />

      {outputError ? <div className="banner error">{outputError}</div> : null}

      <UniversalDataTable
        table={table}
        skeletonCols={11}
        toolbar={
          <div className="run-history-filters">
            <label>
              {scraperLabels.runFilterAdapter}
              <select
                className="input"
                value={table.filters.adapter_key ?? ""}
                onChange={(event) => table.setFilter("adapter_key", event.target.value)}
              >
                <option value="">{scraperLabels.runFilterAll}</option>
                {adapters.map((adapter) => (
                  <option key={adapter.adapter_key} value={adapter.adapter_key}>
                    {adapter.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {scraperLabels.runFilterStatus}
              <select
                className="input"
                value={table.filters.status ?? ""}
                onChange={(event) => table.setFilter("status", event.target.value)}
              >
                <option value="">{scraperLabels.runFilterAll}</option>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {runStatusLabel(status)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {scraperLabels.runFilterEngineType}
              <select
                className="input"
                value={table.filters.engine_type ?? ""}
                onChange={(event) => table.setFilter("engine_type", event.target.value)}
              >
                <option value="">{scraperLabels.runFilterAll}</option>
                <option value="static">{scraperLabels.runEngineTypeStatic}</option>
                <option value="dynamic">{scraperLabels.runEngineTypeDynamic}</option>
              </select>
            </label>
            <label>
              {scraperLabels.runFilterDateFrom}
              <input
                className="input"
                type="date"
                value={table.filters.date_from ?? ""}
                onChange={(event) => table.setFilter("date_from", event.target.value)}
              />
            </label>
            <label>
              {scraperLabels.runFilterDateTo}
              <input
                className="input"
                type="date"
                value={table.filters.date_to ?? ""}
                onChange={(event) => table.setFilter("date_to", event.target.value)}
              />
            </label>
            <label className="run-history-url-filter">
              {scraperLabels.runFilterUrl}
              <input
                className="input"
                type="search"
                value={table.search}
                placeholder="https://"
                onChange={(event) => table.setSearch(event.target.value)}
              />
            </label>
          </div>
        }
        columns={columns}
        rowKey={(run) => run.id}
        emptyState={<p className="text-muted">{scraperLabels.runHistoryEmpty}</p>}
        className="scraper-run-history-table"
      />
    </div>
  );
}
