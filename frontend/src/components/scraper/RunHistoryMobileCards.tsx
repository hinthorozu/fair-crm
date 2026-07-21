import React from "react";
import { Badge } from "../ui/Badge";
import { scraperLabels } from "../../labels/scraperLabels";
import type { ScraperRun } from "../../types/scraper";
import { runStatusBadgeVariant, runStatusLabel } from "../../utils/scraperBadges";

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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="run-history-card-field">
      <span className="run-history-card-label">{label}</span>
      <div className="run-history-card-value">{children}</div>
    </div>
  );
}

export interface RunHistoryMobileCardsProps {
  items: ScraperRun[];
  onOpenAdapter?: (adapterKey: string) => void;
  onOpenRunDetail?: (adapterKey: string, runId: string) => void;
  onOpenImportBatch?: (batchId: string) => void;
  filesMenu: (run: ScraperRun) => React.ReactNode;
}

export function RunHistoryMobileCards({
  items,
  onOpenAdapter,
  onOpenRunDetail,
  onOpenImportBatch,
  filesMenu,
}: RunHistoryMobileCardsProps) {
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(() => new Set());
  const [techOpenIds, setTechOpenIds] = React.useState<Set<string>>(() => new Set());

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleTech = (id: string) => {
    setTechOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <ul className="run-history-mobile-list">
      {items.map((run) => {
        const expanded = expandedIds.has(run.id);
        const techOpen = techOpenIds.has(run.id);
        return (
          <li key={run.id} className={`run-history-card${expanded ? " is-expanded" : ""}`}>
            <div className="run-history-card-summary">
              <Field label={scraperLabels.runColStarted}>{formatDateTime(run.started_at)}</Field>
              <Field label={scraperLabels.runColSource}>{runSourceLabel(run.run_source)}</Field>
              <Field label={scraperLabels.runColStatus}>
                <Badge variant={runStatusBadgeVariant(run.status)}>{runStatusLabel(run.status)}</Badge>
              </Field>
              <Field label={scraperLabels.runColRows}>{run.total_rows.toLocaleString("tr-TR")}</Field>
              <Field label={scraperLabels.runColDuration}>{formatDurationMs(run.duration_ms)}</Field>

              <div className="run-history-card-actions">
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => onOpenRunDetail?.(run.adapter_key, run.id)}
                >
                  {scraperLabels.actionDetail}
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  aria-expanded={expanded}
                  onClick={() => toggleExpanded(run.id)}
                >
                  {expanded ? scraperLabels.runHistoryHideDetails : scraperLabels.runHistoryShowDetails}
                </button>
              </div>
            </div>

            {expanded ? (
              <div className="run-history-card-details">
                <Field label={scraperLabels.runColFairName}>{run.fair_name ?? "—"}</Field>
                <Field label={scraperLabels.runColAdapterName}>
                  {onOpenAdapter ? (
                    <button
                      type="button"
                      className="btn link run-history-card-link"
                      onClick={() => onOpenAdapter(run.adapter_key)}
                    >
                      {run.adapter_name ?? run.adapter_key}
                    </button>
                  ) : (
                    (run.adapter_name ?? run.adapter_key)
                  )}
                </Field>
                <Field label={scraperLabels.runColEngineType}>{engineTypeLabel(run.engine_type)}</Field>
                <Field label={scraperLabels.runColInputUrl}>
                  {run.input_url ? (
                    <a
                      href={run.input_url}
                      target="_blank"
                      rel="noreferrer"
                      className="run-history-url run-history-card-link"
                    >
                      {run.input_url}
                    </a>
                  ) : (
                    "—"
                  )}
                </Field>
                <Field label={scraperLabels.runColFiles}>{filesMenu(run)}</Field>
                <Field label={scraperLabels.runColImportBatch}>
                  {run.import_batch_id && onOpenImportBatch ? (
                    <button
                      type="button"
                      className="btn link run-history-card-link"
                      onClick={() => onOpenImportBatch(run.import_batch_id!)}
                    >
                      {scraperLabels.actionOpenImport}
                    </button>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </Field>
                {run.error_message ? (
                  <Field label={scraperLabels.runColError}>
                    <span className="run-history-card-error">{run.error_message}</span>
                  </Field>
                ) : null}

                <div className="run-history-card-tech">
                  <button
                    type="button"
                    className="run-history-card-tech-toggle"
                    aria-expanded={techOpen}
                    onClick={() => toggleTech(run.id)}
                  >
                    {scraperLabels.runHistoryTechnicalDetails}
                    <span aria-hidden>{techOpen ? "▾" : "▸"}</span>
                  </button>
                  {techOpen ? (
                    <div className="run-history-card-tech-body">
                      <Field label={scraperLabels.runColAdapterKey}>{run.adapter_key}</Field>
                      <Field label={scraperLabels.runColEngineKey}>{run.engine_key ?? "—"}</Field>
                      <Field label={scraperLabels.runColRunId}>
                        <code className="run-history-card-code">{run.id}</code>
                      </Field>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
