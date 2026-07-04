import React from "react";
import { getScraperManifest } from "../../api/scraper";
import { Tabs, TabPanel } from "../ui/Tabs";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { DetailValue, formatDetailDate } from "../ui/DetailFields";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { AdapterFeatureBadges } from "./AdapterFeatureBadges";
import { AdapterRunLogConsole } from "./AdapterRunLogConsole";
import { AdapterLinkedFairsTab } from "./AdapterLinkedFairsTab";
import { scraperLabels } from "../../labels/scraperLabels";
import {
  adapterStatusBadgeVariant,
  adapterStatusLabel,
  runStatusBadgeVariant,
  runStatusLabel,
} from "../../utils/scraperBadges";
import type { AdapterListItem, ScraperManifest, ScraperRun } from "../../types/scraper";

export type AdapterDetailTab = "general" | "manifest" | "runs" | "console" | "fairs";

export interface AdapterDetailContentProps {
  adapterKey: string;
  adapterItem: AdapterListItem | null;
  runs: ScraperRun[];
  activeTab: AdapterDetailTab;
  onTabChange: (tab: AdapterDetailTab) => void;
  onOpenFair?: (fairId: string) => void;
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

function ManifestField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
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

function ManifestDetails({ manifest }: { manifest: ScraperManifest }) {
  return (
    <dl className="detail-grid adapter-manifest-fields">
      <ManifestField label="Adapter Key" value={<DetailValue value={manifest.adapter_key} />} />
      <ManifestField label="Display Name" value={<DetailValue value={manifest.display_name} />} />
      <ManifestField label="Version" value={<DetailValue value={manifest.version} />} />
      <ManifestField label="Status" value={adapterStatusLabel(manifest.status)} />
      <ManifestField label="Author" value={<DetailValue value={manifest.author} />} />
      <ManifestField label="Scraper Version" value={<DetailValue value={manifest.scraper_version} />} />
      <ManifestField label="Target Site Version" value={<DetailValue value={manifest.target_site_version} />} />
      <ManifestField label="Last Verified" value={formatDetailDate(manifest.last_verified)} />
      <ManifestField
        label={scraperLabels.manifestSites}
        value={
          manifest.supported_sites.length ? (
            <ul className="detail-collection-list">
              {manifest.supported_sites.map((site) => (
                <li key={site}>{site}</li>
              ))}
            </ul>
          ) : (
            "—"
          )
        }
      />
      <ManifestField label="Notes" value={<DetailValue value={manifest.notes} />} />
      <ManifestField
        label={scraperLabels.manifestOutput}
        value={`JSON: ${manifest.output.json_handoff ? "Evet" : "Hayır"}, Excel: ${manifest.output.excel ? "Evet" : "Hayır"}`}
      />
      <ManifestField
        label={scraperLabels.manifestBrowser}
        value={`JS: ${manifest.browser.requires_js ? "Evet" : "Hayır"}, Playwright: ${manifest.browser.requires_playwright ? "Evet" : "Hayır"}`}
      />
      <ManifestField
        label={scraperLabels.manifestSupports}
        value={
          <ul className="detail-collection-list">
            {Object.entries(manifest.supports).map(([key, enabled]) => (
              <li key={key}>
                {key}: {enabled ? "Evet" : "Hayır"}
              </li>
            ))}
          </ul>
        }
      />
    </dl>
  );
}

export function AdapterDetailContent({
  adapterKey,
  adapterItem,
  runs,
  activeTab,
  onTabChange,
  onOpenFair,
}: AdapterDetailContentProps) {
  const [manifest, setManifest] = React.useState<ScraperManifest | null>(null);
  const [manifestLoading, setManifestLoading] = React.useState(true);
  const [manifestError, setManifestError] = React.useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);

  const adapterRuns = React.useMemo(
    () => runs.filter((run) => run.adapter_key === adapterKey),
    [runs, adapterKey],
  );

  React.useEffect(() => {
    let cancelled = false;
    setManifestLoading(true);
    setManifestError(null);
    void getScraperManifest(adapterKey)
      .then((data) => {
        if (!cancelled) setManifest(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setManifestError(err instanceof Error ? err.message : scraperLabels.loadError);
        }
      })
      .finally(() => {
        if (!cancelled) setManifestLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [adapterKey]);

  const openRunInConsole = React.useCallback(
    (runId: string) => {
      setSelectedRunId(runId);
      onTabChange("console");
    },
    [onTabChange],
  );

  const runColumns = React.useMemo(() => buildRunColumns(openRunInConsole), [openRunInConsole]);

  return (
    <>
      <Tabs
        items={[
          { id: "general", label: scraperLabels.drawerTabGeneral },
          { id: "manifest", label: scraperLabels.drawerTabManifest },
          { id: "runs", label: scraperLabels.drawerTabRunHistory, badge: adapterRuns.length },
          { id: "console", label: scraperLabels.drawerTabTestConsole },
          { id: "fairs", label: scraperLabels.drawerTabLinkedFairs },
        ]}
        active={activeTab}
        onChange={onTabChange}
      />

      <TabPanel id="panel-general" labelledBy="tab-general" active={activeTab === "general"}>
        <Card>
          {manifestLoading ? <p className="text-muted">Yükleniyor…</p> : null}
          {manifestError ? <p className="text-danger">{manifestError}</p> : null}
          {manifest ? (
            <dl className="detail-grid">
              <ManifestField label="Adapter" value={<DetailValue value={manifest.display_name} />} />
              <ManifestField
                label="Status"
                value={
                  <Badge variant={adapterStatusBadgeVariant(manifest.status)}>
                    {adapterStatusLabel(manifest.status)}
                  </Badge>
                }
              />
              <ManifestField label="Version" value={<DetailValue value={manifest.version} />} />
              <ManifestField label="Last Verified" value={formatDetailDate(manifest.last_verified)} />
              <ManifestField
                label={scraperLabels.colFeatures}
                value={<AdapterFeatureBadges features={adapterItem?.features ?? []} />}
              />
              <ManifestField label="Notes" value={<DetailValue value={manifest.notes} />} />
            </dl>
          ) : null}
        </Card>
      </TabPanel>

      <TabPanel id="panel-manifest" labelledBy="tab-manifest" active={activeTab === "manifest"}>
        <Card>
          {manifestLoading ? <p className="text-muted">Yükleniyor…</p> : null}
          {manifestError ? <p className="text-danger">{manifestError}</p> : null}
          {manifest ? <ManifestDetails manifest={manifest} /> : null}
        </Card>
      </TabPanel>

      <TabPanel id="panel-runs" labelledBy="tab-runs" active={activeTab === "runs"}>
        <Card>
          <UniversalDataTable
            items={adapterRuns}
            columns={runColumns}
            rowKey={(run) => run.id}
            emptyState={<p className="text-muted">{scraperLabels.runsEmpty}</p>}
            className="adapter-runs-table"
          />
        </Card>
      </TabPanel>

      <TabPanel id="panel-console" labelledBy="tab-console" active={activeTab === "console"}>
        <Card>
          <AdapterRunLogConsole
            runs={adapterRuns}
            selectedRunId={selectedRunId}
            onSelectRunId={setSelectedRunId}
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
