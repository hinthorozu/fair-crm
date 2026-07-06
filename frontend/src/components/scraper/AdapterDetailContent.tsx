import React from "react";
import { Tabs, TabPanel } from "../ui/Tabs";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { AdapterLinkedFairsTab } from "./AdapterLinkedFairsTab";
import { AdapterForm } from "./AdapterForm";
import { scraperLabels } from "../../labels/scraperLabels";
import {
  runStatusBadgeVariant,
  runStatusLabel,
} from "../../utils/scraperBadges";
import type { ScraperManifest, ScraperRun } from "../../types/scraper";
import {
  manifestCapabilities,
  manifestToFormState,
  type AdapterFormState,
} from "../../utils/adapterManifestForm";
import { EnrichmentRunPanel } from "./EnrichmentRunPanel";
import { isCustomerContactEnrichmentAdapter } from "../../utils/enrichmentAdapter";

export type AdapterDetailTab = "manifest" | "run" | "runs" | "fairs";

export interface AdapterDetailContentProps {
  adapterKey: string;
  runs: ScraperRun[];
  activeTab: AdapterDetailTab;
  onTabChange: (tab: AdapterDetailTab) => void;
  onOpenFair?: (fairId: string) => void;
  onViewAllRuns?: (adapterKey: string) => void;
  onOpenScraperTest?: (adapterKey: string, runId?: string) => void;
  onRunsChanged?: () => void;
  manifest: ScraperManifest | null;
  manifestLoading: boolean;
  manifestError: string | null;
  isEditing: boolean;
  draft: AdapterFormState | null;
  onDraftChange: (updater: (current: AdapterFormState) => AdapterFormState) => void;
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

function buildRunColumns(onSelectRun: (runId: string) => void): UniversalDataTableColumn<ScraperRun>[] {
  return [
    {
      key: "started_at",
      title: scraperLabels.runColStarted,
      sortable: false,
      render: (run) => (
        <button type="button" className="btn link" onClick={() => onSelectRun(run.id)}>
          {formatDateTime(run.started_at)}
        </button>
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
  ];
}

function ManifestTabPanel({
  manifest,
  isEditing,
  draft,
  onDraftChange,
}: {
  manifest: ScraperManifest;
  isEditing: boolean;
  draft: AdapterFormState | null;
  onDraftChange: AdapterDetailContentProps["onDraftChange"];
}) {
  const capabilities = manifestCapabilities(manifest);
  const metadata = {
    adapter_key: manifest.adapter_key,
    author: manifest.author,
    scraper_version: manifest.scraper_version,
  };

  if (isEditing && draft) {
    return (
      <AdapterForm
        mode="edit"
        values={draft}
        onChange={onDraftChange}
        capabilities={capabilities}
        metadata={metadata}
      />
    );
  }

  return (
    <AdapterForm
      mode="readOnly"
      values={manifestToFormState(manifest)}
      onChange={() => undefined}
      capabilities={capabilities}
      metadata={metadata}
    />
  );
}

export function AdapterDetailContent({
  adapterKey,
  runs,
  activeTab,
  onTabChange,
  onOpenFair,
  onViewAllRuns,
  onOpenScraperTest,
  onRunsChanged,
  manifest,
  manifestLoading,
  manifestError,
  isEditing,
  draft,
  onDraftChange,
}: AdapterDetailContentProps) {
  const adapterRuns = React.useMemo(
    () => runs.filter((run) => run.adapter_key === adapterKey).slice(0, 5),
    [runs, adapterKey],
  );

  const openRunInTest = React.useCallback(
    (runId: string) => {
      onOpenScraperTest?.(adapterKey, runId);
    },
    [adapterKey, onOpenScraperTest],
  );

  const runColumns = React.useMemo(() => buildRunColumns(openRunInTest), [openRunInTest]);
  const isEnrichmentAdapter = isCustomerContactEnrichmentAdapter(adapterKey);

  return (
    <>
      <Tabs
        items={[
          { id: "manifest", label: scraperLabels.drawerTabManifest },
          ...(isEnrichmentAdapter
            ? [{ id: "run" as const, label: scraperLabels.enrichmentRunTab }]
            : []),
          { id: "runs", label: scraperLabels.drawerTabRunHistory, badge: adapterRuns.length },
          { id: "fairs", label: scraperLabels.drawerTabLinkedFairs },
        ]}
        active={activeTab}
        onChange={onTabChange}
      />

      <TabPanel id="panel-manifest" labelledBy="tab-manifest" active={activeTab === "manifest"}>
        <Card>
          {manifestLoading ? <p className="text-muted">Yükleniyor…</p> : null}
          {manifestError ? <p className="text-danger">{manifestError}</p> : null}
          {manifest ? (
            <ManifestTabPanel
              manifest={manifest}
              isEditing={isEditing}
              draft={draft}
              onDraftChange={onDraftChange}
            />
          ) : null}
        </Card>
      </TabPanel>

      {isEnrichmentAdapter ? (
        <TabPanel id="panel-run" labelledBy="tab-run" active={activeTab === "run"}>
          <Card>
            {manifest ? (
              <EnrichmentRunPanel
                adapterKey={adapterKey}
                manifest={manifest}
                onRunFinished={onRunsChanged}
              />
            ) : (
              <p className="text-muted">Yükleniyor…</p>
            )}
          </Card>
        </TabPanel>
      ) : null}

      <TabPanel id="panel-runs" labelledBy="tab-runs" active={activeTab === "runs"}>
        <Card>
          <div className="adapter-runs-summary-header">
            <p className="text-muted">{scraperLabels.runRecentSummary}</p>
            <div className="adapter-runs-summary-actions">
              {!isEnrichmentAdapter && onOpenScraperTest ? (
                <button type="button" className="btn link" onClick={() => onOpenScraperTest(adapterKey)}>
                  {scraperLabels.openScraperTestForAdapter}
                </button>
              ) : null}
              {onViewAllRuns ? (
                <button type="button" className="btn link" onClick={() => onViewAllRuns(adapterKey)}>
                  {scraperLabels.runViewAllHistory}
                </button>
              ) : null}
            </div>
          </div>
          <UniversalDataTable
            items={adapterRuns}
            columns={runColumns}
            rowKey={(run) => run.id}
            emptyState={<p className="text-muted">{scraperLabels.runsEmpty}</p>}
            className="adapter-runs-table"
          />
        </Card>
      </TabPanel>

      <TabPanel id="panel-fairs" labelledBy="tab-fairs" active={activeTab === "fairs"}>
        <Card>
          <AdapterLinkedFairsTab adapterKey={adapterKey} active={activeTab === "fairs"} onOpenFair={onOpenFair} />
        </Card>
      </TabPanel>
    </>
  );
}
