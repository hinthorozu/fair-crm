import React from "react";
import { importLabels } from "../../labels/importLabels";
import type { MappingColumnPreview } from "../../types/import";

const PREVIEW_TRUNCATE = 40;
const DEFAULT_SAMPLE_ROWS = 3;
const MAX_SAMPLE_ROWS = 10;

function formatSampleValue(value: unknown | null): string {
  if (value === null || value === undefined) return "—";
  const text = String(value).trim();
  return text || "—";
}

function renderSampleText(value: unknown | null): React.ReactNode {
  const full = formatSampleValue(value);
  if (full === "—") return <span className="mapping-sample-empty">—</span>;
  if (full.length > PREVIEW_TRUNCATE) {
    return (
      <span className="mapping-sample-value" title={full}>
        {full.slice(0, PREVIEW_TRUNCATE)}…
      </span>
    );
  }
  return <span className="mapping-sample-value">{full}</span>;
}

export function columnOptionLabel(col: MappingColumnPreview, headerMode: string): string {
  if (headerMode === "no_header") {
    return `Column ${col.letter}`;
  }
  return col.header ? `${col.header} (${col.letter})` : `Column ${col.letter}`;
}

interface MappingFieldPreviewProps {
  column: MappingColumnPreview | undefined;
  showAll: boolean;
}

export function MappingFieldPreview({ column, showAll }: MappingFieldPreviewProps) {
  if (!column) {
    return <span className="text-muted">{importLabels.mappingNoColumnSelected}</span>;
  }

  const samples = column.samples ?? [];
  const visibleCount = showAll
    ? Math.min(MAX_SAMPLE_ROWS, samples.length)
    : Math.min(DEFAULT_SAMPLE_ROWS, samples.length);
  const visibleSamples = samples.slice(0, visibleCount);

  return (
    <div className="mapping-field-preview">
      <ul className="mapping-sample-list">
        {visibleSamples.map((sample, index) => (
          <li key={index}>{renderSampleText(sample)}</li>
        ))}
      </ul>
      <div className="mapping-column-stats">
        <span>{importLabels.mappingStatsTotal}: {column.stats.total}</span>
        <span>{importLabels.mappingStatsEmpty}: {column.stats.empty}</span>
        <span>{importLabels.mappingStatsFilled}: {column.stats.filled}</span>
        {column.stats.first_value && (
          <span>
            {importLabels.mappingStatsFirst}: {column.stats.first_value.length > PREVIEW_TRUNCATE
              ? `${column.stats.first_value.slice(0, PREVIEW_TRUNCATE)}…`
              : column.stats.first_value}
          </span>
        )}
      </div>
    </div>
  );
}

export { DEFAULT_SAMPLE_ROWS, MAX_SAMPLE_ROWS };
