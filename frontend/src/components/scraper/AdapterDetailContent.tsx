import React from "react";
import { Tabs, TabPanel } from "../ui/Tabs";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { DetailValue, formatDetailDate } from "../ui/DetailFields";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { AdapterRunLogConsole } from "./AdapterRunLogConsole";
import { AdapterLinkedFairsTab } from "./AdapterLinkedFairsTab";
import { scraperLabels, FEATURE_SHORT_LABELS } from "../../labels/scraperLabels";
import {
  adapterStatusBadgeVariant,
  adapterStatusLabel,
  runStatusBadgeVariant,
  runStatusLabel,
} from "../../utils/scraperBadges";
import type { ScraperManifest, ScraperRun, ScraperSupports } from "../../types/scraper";
import {
  SUPPORT_KEYS,
  type AdapterEditFormState,
} from "../../utils/adapterManifestForm";

export type AdapterDetailTab = "general" | "manifest" | "runs" | "console" | "fairs";

export interface AdapterDetailContentProps {
  adapterKey: string;
  runs: ScraperRun[];
  activeTab: AdapterDetailTab;
  onTabChange: (tab: AdapterDetailTab) => void;
  onOpenFair?: (fairId: string) => void;
  manifest: ScraperManifest | null;
  manifestLoading: boolean;
  manifestError: string | null;
  isEditing: boolean;
  draft: AdapterEditFormState | null;
  onDraftChange: (updater: (current: AdapterEditFormState) => AdapterEditFormState) => void;
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

function SupportCheckboxes({
  supports,
  onChange,
}: {
  supports: ScraperSupports;
  onChange: (key: keyof ScraperSupports, enabled: boolean) => void;
}) {
  return (
    <ul className="detail-collection-list adapter-manifest-checkboxes">
      {SUPPORT_KEYS.map((key) => (
        <li key={key}>
          <label>
            <input
              type="checkbox"
              checked={supports[key]}
              onChange={(event) => onChange(key, event.target.checked)}
            />{" "}
            {FEATURE_SHORT_LABELS[key] ?? key}
          </label>
        </li>
      ))}
    </ul>
  );
}

function ManifestDetailsView({ manifest }: { manifest: ScraperManifest }) {
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

function GeneralTabPanel({
  manifest,
  isEditing,
  draft,
  onDraftChange,
}: {
  manifest: ScraperManifest;
  isEditing: boolean;
  draft: AdapterEditFormState | null;
  onDraftChange: AdapterDetailContentProps["onDraftChange"];
}) {
  if (isEditing && draft) {
    return (
      <dl className="detail-grid adapter-manifest-fields">
        <ManifestField label="Adapter Key" value={<DetailValue value={manifest.adapter_key} />} />
        <ManifestField
          label={scraperLabels.formAdapterName}
          value={
            <input
              className="input"
              value={draft.display_name}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, display_name: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.colVersion}
          value={
            <input
              className="input"
              value={draft.version}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, version: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.colStatus}
          value={
            <select
              className="input"
              value={draft.status}
              onChange={(event) =>
                onDraftChange((current) => ({
                  ...current,
                  status: event.target.value as AdapterEditFormState["status"],
                }))
              }
            >
              <option value="stable">{scraperLabels.statusStable}</option>
              <option value="experimental">{scraperLabels.statusExperimental}</option>
              <option value="deprecated">{scraperLabels.statusDeprecated}</option>
            </select>
          }
        />
        <ManifestField
          label={scraperLabels.colLastVerified}
          value={
            <input
              className="input"
              type="date"
              value={draft.last_verified}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, last_verified: event.target.value }))
              }
            />
          }
        />
        <ManifestField label="Author" value={<DetailValue value={manifest.author} />} />
        <ManifestField label="Scraper Version" value={<DetailValue value={manifest.scraper_version} />} />
        <ManifestField label="Target Site Version" value={<DetailValue value={manifest.target_site_version} />} />
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
        <ManifestField
          label={scraperLabels.manifestNotes}
          value={
            <textarea
              className="input"
              rows={3}
              value={draft.notes}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, notes: event.target.value }))
              }
            />
          }
        />
      </dl>
    );
  }

  return (
    <dl className="detail-grid">
      <ManifestField label="Adapter Key" value={<DetailValue value={manifest.adapter_key} />} />
      <ManifestField label={scraperLabels.formAdapterName} value={<DetailValue value={manifest.display_name} />} />
      <ManifestField label={scraperLabels.colVersion} value={<DetailValue value={manifest.version} />} />
      <ManifestField
        label={scraperLabels.colStatus}
        value={
          <Badge variant={adapterStatusBadgeVariant(manifest.status)}>
            {adapterStatusLabel(manifest.status)}
          </Badge>
        }
      />
      <ManifestField label={scraperLabels.colLastVerified} value={formatDetailDate(manifest.last_verified)} />
      <ManifestField label="Author" value={<DetailValue value={manifest.author} />} />
      <ManifestField label="Scraper Version" value={<DetailValue value={manifest.scraper_version} />} />
      <ManifestField label="Target Site Version" value={<DetailValue value={manifest.target_site_version} />} />
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
      <ManifestField label={scraperLabels.manifestNotes} value={<DetailValue value={manifest.notes} />} />
    </dl>
  );
}

function ManifestTabPanel({
  manifest,
  isEditing,
  draft,
  onDraftChange,
}: {
  manifest: ScraperManifest;
  isEditing: boolean;
  draft: AdapterEditFormState | null;
  onDraftChange: AdapterDetailContentProps["onDraftChange"];
}) {
  if (isEditing && draft) {
    const setSupport = (key: keyof ScraperSupports, enabled: boolean) => {
      onDraftChange((current) => ({
        ...current,
        supports: { ...current.supports, [key]: enabled },
      }));
    };

    return (
      <dl className="detail-grid adapter-manifest-fields">
        <ManifestField label="Adapter Key" value={<DetailValue value={manifest.adapter_key} />} />
        <ManifestField
          label={scraperLabels.formAdapterName}
          value={
            <input
              className="input"
              value={draft.display_name}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, display_name: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.colVersion}
          value={
            <input
              className="input"
              value={draft.version}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, version: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.colStatus}
          value={
            <select
              className="input"
              value={draft.status}
              onChange={(event) =>
                onDraftChange((current) => ({
                  ...current,
                  status: event.target.value as AdapterEditFormState["status"],
                }))
              }
            >
              <option value="stable">{scraperLabels.statusStable}</option>
              <option value="experimental">{scraperLabels.statusExperimental}</option>
              <option value="deprecated">{scraperLabels.statusDeprecated}</option>
            </select>
          }
        />
        <ManifestField label="Author" value={<DetailValue value={manifest.author} />} />
        <ManifestField label="Scraper Version" value={<DetailValue value={manifest.scraper_version} />} />
        <ManifestField label="Target Site Version" value={<DetailValue value={manifest.target_site_version} />} />
        <ManifestField
          label={scraperLabels.manifestSites}
          value={
            <textarea
              className="input"
              rows={3}
              value={draft.supported_sites}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, supported_sites: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.manifestNotes}
          value={
            <textarea
              className="input"
              rows={3}
              value={draft.notes}
              onChange={(event) =>
                onDraftChange((current) => ({ ...current, notes: event.target.value }))
              }
            />
          }
        />
        <ManifestField
          label={scraperLabels.manifestOutput}
          value={
            <div className="adapter-manifest-checkboxes">
              <label>
                <input
                  type="checkbox"
                  checked={draft.output_json_handoff}
                  onChange={(event) =>
                    onDraftChange((current) => ({
                      ...current,
                      output_json_handoff: event.target.checked,
                    }))
                  }
                />{" "}
                JSON Handoff
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={draft.output_excel}
                  onChange={(event) =>
                    onDraftChange((current) => ({ ...current, output_excel: event.target.checked }))
                  }
                />{" "}
                Excel
              </label>
            </div>
          }
        />
        <ManifestField
          label={scraperLabels.manifestBrowser}
          value={
            <div className="adapter-manifest-checkboxes">
              <label>
                <input
                  type="checkbox"
                  checked={draft.browser_requires_js}
                  onChange={(event) =>
                    onDraftChange((current) => ({
                      ...current,
                      browser_requires_js: event.target.checked,
                    }))
                  }
                />{" "}
                JS
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={draft.browser_requires_playwright}
                  onChange={(event) =>
                    onDraftChange((current) => ({
                      ...current,
                      browser_requires_playwright: event.target.checked,
                    }))
                  }
                />{" "}
                Playwright
              </label>
            </div>
          }
        />
        <ManifestField
          label={scraperLabels.manifestSupports}
          value={<SupportCheckboxes supports={draft.supports} onChange={setSupport} />}
        />
      </dl>
    );
  }

  return <ManifestDetailsView manifest={manifest} />;
}

export function AdapterDetailContent({
  adapterKey,
  runs,
  activeTab,
  onTabChange,
  onOpenFair,
  manifest,
  manifestLoading,
  manifestError,
  isEditing,
  draft,
  onDraftChange,
}: AdapterDetailContentProps) {
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);

  const adapterRuns = React.useMemo(
    () => runs.filter((run) => run.adapter_key === adapterKey),
    [runs, adapterKey],
  );

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
            <GeneralTabPanel
              manifest={manifest}
              isEditing={isEditing}
              draft={draft}
              onDraftChange={onDraftChange}
            />
          ) : null}
        </Card>
      </TabPanel>

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
          <AdapterRunLogConsole adapterKey={adapterKey} focusRunId={selectedRunId} />
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
