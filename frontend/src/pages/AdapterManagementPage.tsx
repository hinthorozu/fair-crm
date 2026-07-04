import React from "react";
import { ApiError } from "../api/client";
import {
  activateAdapter,
  createAdapter,
  deactivateAdapter,
  getScraperDashboard,
  getScraperManifests,
  listAdapters,
  listScraperRuns,
} from "../api/scraper";
import { AdapterFormModal } from "../components/scraper/AdapterFormModal";
import { AdapterFeatureBadges } from "../components/scraper/AdapterFeatureBadges";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { labels } from "../labels";
import { scraperLabels } from "../labels/scraperLabels";
import type {
  AdapterListItem,
  CreateAdapterPayload,
  ScraperDashboardSummary,
  ScraperRun,
} from "../types/scraper";
import { formatDetailDate } from "../components/ui/DetailFields";
import { adapterDetailToListItem, mergeAdapterListItem } from "../utils/scraperAdapters";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function buildLastRunMap(runs: ScraperRun[]): Map<string, ScraperRun> {
  const map = new Map<string, ScraperRun>();
  for (const run of runs) {
    const existing = map.get(run.adapter_key);
    if (!existing || new Date(run.started_at).getTime() > new Date(existing.started_at).getTime()) {
      map.set(run.adapter_key, run);
    }
  }
  return map;
}

function buildAdapterColumns(handlers: {
  onOpenDetail: (adapter: AdapterListItem) => void;
  onToggleActive: (adapter: AdapterListItem) => void;
  togglingKey: string | null;
  lastRunMap: Map<string, ScraperRun>;
}): UniversalDataTableColumn<AdapterListItem>[] {
  return [
    {
      key: "display_name",
      title: scraperLabels.colAdapter,
      sortable: true,
      render: (adapter) => (
        <div className="adapter-name-cell">
          <span className="adapter-name-primary">{adapter.display_name}</span>
          <span className="adapter-name-secondary text-muted">{adapter.adapter_key}</span>
          {!adapter.is_active ? (
            <Badge variant="neutral">{scraperLabels.inactiveBadge}</Badge>
          ) : null}
        </div>
      ),
    },
    {
      key: "version",
      title: scraperLabels.colVersion,
      sortable: true,
      render: (adapter) => adapter.version,
    },
    {
      key: "features",
      title: scraperLabels.colFeatures,
      sortable: false,
      className: "adapter-col-features",
      render: (adapter) => <AdapterFeatureBadges features={adapter.features} />,
    },
    {
      key: "last_run",
      title: scraperLabels.colLastRun,
      sortable: false,
      render: (adapter) => formatDateTime(handlers.lastRunMap.get(adapter.adapter_key)?.started_at),
    },
    {
      key: "last_verified",
      title: scraperLabels.colLastVerified,
      sortable: true,
      render: (adapter) => formatDetailDate(adapter.last_verified),
    },
    {
      key: "actions",
      title: scraperLabels.colActions,
      sortable: false,
      render: (adapter) => (
        <div className="adapter-list-actions">
          <button type="button" className="btn btn-sm secondary" onClick={() => handlers.onOpenDetail(adapter)}>
            {scraperLabels.actionDetail}
          </button>
          <button
            type="button"
            className="btn btn-sm secondary"
            disabled={handlers.togglingKey === adapter.adapter_key}
            onClick={() => handlers.onToggleActive(adapter)}
          >
            {adapter.is_active ? scraperLabels.actionDeactivate : scraperLabels.actionActivate}
          </button>
        </div>
      ),
    },
  ];
}

function SummaryCards({
  summary,
  lastRunLabel,
}: {
  summary: ScraperDashboardSummary;
  lastRunLabel: string;
}) {
  const cards = [
    { label: scraperLabels.summaryTotal, value: summary.total_adapters.toLocaleString("tr-TR") },
    { label: scraperLabels.summaryLastRun, value: lastRunLabel },
    { label: scraperLabels.summaryLastError, value: summary.failed_scraper_count.toLocaleString("tr-TR") },
  ];

  return (
    <div className="adapter-summary-grid">
      {cards.map((card) => (
        <div key={card.label} className="adapter-summary-card card">
          <p className="adapter-summary-label">{card.label}</p>
          <p className="adapter-summary-value">{card.value}</p>
        </div>
      ))}
    </div>
  );
}

export function AdapterManagementPage({
  onOpenDetail,
}: {
  onOpenDetail?: (adapterKey: string) => void;
}) {
  const [summary, setSummary] = React.useState<ScraperDashboardSummary | null>(null);
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [runs, setRuns] = React.useState<ScraperRun[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [formSaving, setFormSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [togglingKey, setTogglingKey] = React.useState<string | null>(null);

  const refreshAdapters = React.useCallback(async (): Promise<AdapterListItem[]> => {
    try {
      const adapterList = await listAdapters();
      setAdapters(adapterList.items);
      return adapterList.items;
    } catch (primaryErr) {
      try {
        const manifests = await getScraperManifests();
        const fallback = manifests.items.map((item) => ({
          ...item,
          id: item.id ?? null,
          is_active: item.is_active ?? true,
          is_registered: item.is_registered ?? true,
        }));
        setAdapters(fallback);
      } catch {
        // Keep current list if both adapter and manifest endpoints fail.
      }
      throw primaryErr;
    }
  }, []);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const errors: string[] = [];

    try {
      const dashboard = await getScraperDashboard();
      setSummary(dashboard.summary);
    } catch (err) {
      errors.push(err instanceof ApiError ? err.message : scraperLabels.loadError);
    }

    try {
      await refreshAdapters();
    } catch (err) {
      errors.push(err instanceof ApiError ? err.message : scraperLabels.loadError);
    }

    try {
      const runList = await listScraperRuns({ limit: 200 });
      setRuns(runList.items);
    } catch (err) {
      errors.push(err instanceof ApiError ? err.message : scraperLabels.loadError);
    }

    if (errors.length > 0) {
      setError(errors[0]);
    }
    setLoading(false);
  }, [refreshAdapters]);

  React.useEffect(() => {
    void loadData();
  }, [loadData]);

  const lastRunMap = React.useMemo(() => buildLastRunMap(runs), [runs]);

  const filteredAdapters = React.useMemo(() => {
    const query = search.trim().toLowerCase();
    return adapters.filter((adapter) => {
      if (!query) return true;
      return (
        adapter.display_name.toLowerCase().includes(query) ||
        adapter.adapter_key.toLowerCase().includes(query)
      );
    });
  }, [adapters, search]);

  const lastRunLabel = React.useMemo(() => {
    if (!summary?.last_run_adapter) return "—";
    const match = adapters.find((adapter) => adapter.adapter_key === summary.last_run_adapter);
    return match?.display_name ?? summary.last_run_adapter;
  }, [summary, adapters]);

  const openDetail = React.useCallback(
    (adapter: AdapterListItem) => {
      onOpenDetail?.(adapter.adapter_key);
    },
    [onOpenDetail],
  );

  const handleCreate = React.useCallback(
    async (payload: CreateAdapterPayload) => {
      setFormSaving(true);
      setFormError(null);
      try {
        const created = await createAdapter(payload);
        const listItem = adapterDetailToListItem(created);
        setAdapters((current) => mergeAdapterListItem(current, listItem));
        setSearch("");
        setShowCreateModal(false);
        setFormError(null);
        try {
          await refreshAdapters();
        } catch {
          // List already updated optimistically from POST response.
        }
      } catch (err) {
        const message = err instanceof ApiError ? err.message : scraperLabels.saveError;
        setFormError(message);
        throw err instanceof Error ? err : new Error(message);
      } finally {
        setFormSaving(false);
      }
    },
    [refreshAdapters],
  );

  const handleToggleActive = React.useCallback(
    async (adapter: AdapterListItem) => {
      setTogglingKey(adapter.adapter_key);
      setError(null);
      try {
        const updated = adapter.is_active
          ? await deactivateAdapter(adapter.adapter_key)
          : await activateAdapter(adapter.adapter_key);
        setAdapters((current) => mergeAdapterListItem(current, adapterDetailToListItem(updated)));
        try {
          await refreshAdapters();
        } catch {
          // Keep optimistic toggle from activate/deactivate response.
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : scraperLabels.saveError);
      } finally {
        setTogglingKey(null);
      }
    },
    [refreshAdapters],
  );

  const columns = React.useMemo(
    () =>
      buildAdapterColumns({
        onOpenDetail: openDetail,
        onToggleActive: (adapter) => void handleToggleActive(adapter),
        togglingKey,
        lastRunMap,
      }),
    [openDetail, handleToggleActive, togglingKey, lastRunMap],
  );

  return (
    <div className="adapter-management-page duplicate-groups-page">
      <PageHeader title={scraperLabels.pageTitle} subtitle={scraperLabels.pageSubtitle} />

      {summary ? <SummaryCards summary={summary} lastRunLabel={lastRunLabel} /> : null}

      <div className="card adapter-table-card">
        <div className="adapter-toolbar filters">
          <input
            type="search"
            className="search-input adapter-search-input"
            placeholder={scraperLabels.searchPlaceholder}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label={scraperLabels.searchPlaceholder}
          />
          <div className="adapter-toolbar-actions">
            <button type="button" className="btn secondary" onClick={() => void loadData()} disabled={loading}>
              {labels.refresh}
            </button>
            <button
              type="button"
              className="btn primary"
              onClick={() => {
                setFormError(null);
                setShowCreateModal(true);
              }}
            >
              {scraperLabels.newAdapter}
            </button>
          </div>
        </div>

        {error ? <p className="text-danger adapter-table-error">{error}</p> : null}

        <UniversalDataTable
          items={filteredAdapters}
          columns={columns}
          rowKey={(adapter) => adapter.adapter_key}
          loading={loading}
          error={error}
          onRetry={() => void loadData()}
          emptyState={<EmptyState title={scraperLabels.emptyAdapters} />}
          className="adapter-table"
        />
      </div>

      {showCreateModal ? (
        <AdapterFormModal
          saving={formSaving}
          error={formError}
          onClose={() => {
            setShowCreateModal(false);
            setFormError(null);
          }}
          onSubmit={handleCreate}
        />
      ) : null}
    </div>
  );
}
