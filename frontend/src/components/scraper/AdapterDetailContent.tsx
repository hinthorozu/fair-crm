import React from "react";
import { Tabs, TabPanel } from "../ui/Tabs";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { DetailValue, formatDetailDate } from "../ui/DetailFields";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { AdapterLinkedFairsTab } from "./AdapterLinkedFairsTab";
import { scraperLabels } from "../../labels/scraperLabels";
import {
  runStatusBadgeVariant,
  runStatusLabel,
} from "../../utils/scraperBadges";
import type { ScraperManifest, ScraperRun, RequestedOutputField } from "../../types/scraper";
import {
  DEFAULT_REQUESTED_FIELDS,
  type AdapterEditFormState,
} from "../../utils/adapterManifestForm";
import {
  OutputFieldsSection,
  outputFieldCapabilitiesFromSupports,
  toggleRequestedFieldSelection,
} from "./OutputFieldsSection";

export type AdapterDetailTab = "manifest" | "runs" | "fairs";

export interface AdapterDetailContentProps {
  adapterKey: string;
  runs: ScraperRun[];
  activeTab: AdapterDetailTab;
  onTabChange: (tab: AdapterDetailTab) => void;
  onOpenFair?: (fairId: string) => void;
  onViewAllRuns?: (adapterKey: string) => void;
  onOpenScraperTest?: (adapterKey: string, runId?: string) => void;
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

function ManifestDetailsView({ manifest }: { manifest: ScraperManifest }) {
  return (
    <dl className="detail-grid adapter-manifest-fields">
      <ManifestField label="Adapter Key" value={<DetailValue value={manifest.adapter_key} />} />
      <ManifestField label="Display Name" value={<DetailValue value={manifest.display_name} />} />
      <ManifestField label="Version" value={<DetailValue value={manifest.version} />} />
      <ManifestField label="Author" value={<DetailValue value={manifest.author} />} />
      <ManifestField label="Scraper Version" value={<DetailValue value={manifest.scraper_version} />} />
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
        label={scraperLabels.manifestOutputFields}
        value={
          <OutputFieldsSection
            requestedFields={manifest.requested_fields ?? DEFAULT_REQUESTED_FIELDS}
            capabilities={outputFieldCapabilitiesFromSupports(manifest.supports)}
            readOnly
          />
        }
      />
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
    const toggleRequestedField = (field: RequestedOutputField, enabled: boolean) => {
      onDraftChange((current) => ({
        ...current,
        requested_fields: toggleRequestedFieldSelection(current.requested_fields, field, enabled),
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
          label={scraperLabels.manifestOutputFields}
          value={
            <OutputFieldsSection
              requestedFields={draft.requested_fields}
              capabilities={outputFieldCapabilitiesFromSupports(manifest.supports)}
              onChange={toggleRequestedField}
            />
          }
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
  onViewAllRuns,
  onOpenScraperTest,
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

  return (
    <>
      <Tabs
        items={[
          { id: "manifest", label: scraperLabels.drawerTabManifest },
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

      <TabPanel id="panel-runs" labelledBy="tab-runs" active={activeTab === "runs"}>
        <Card>
          <div className="adapter-runs-summary-header">
            <p className="text-muted">{scraperLabels.runRecentSummary}</p>
            <div className="adapter-runs-summary-actions">
              {onOpenScraperTest ? (
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
