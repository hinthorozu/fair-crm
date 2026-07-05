import React from "react";
import { Badge } from "../../components/ui/Badge";
import type { ImportRow, MergeFieldPreview, MergeOutcome, MergePreview } from "../../types/import";
import { mergeEntityLabels, mergeOutcomeLabels } from "../../labels/importLabels";
import { mergeOutcomeBadgeVariant } from "../../utils/importBadges";

function str(v: string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return v;
}

const MERGE_GROUP_ORDER: Record<string, number> = {
  customer: 0,
  contact: 1,
  participation: 2,
};

function sortMergeGroups(groups: MergePreview["groups"]): MergePreview["groups"] {
  return [...groups].sort(
    (left, right) =>
      (MERGE_GROUP_ORDER[left.entity] ?? 99) - (MERGE_GROUP_ORDER[right.entity] ?? 99),
  );
}

interface MergeDiffViewerProps {
  row: ImportRow;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
}

export function MergeDiffViewer({ row, expanded: controlledExpanded, onExpandedChange }: MergeDiffViewerProps) {
  const [uncontrolledExpanded, setUncontrolledExpanded] = React.useState(false);
  const isControlled = controlledExpanded !== undefined;
  const expanded = isControlled ? controlledExpanded : uncontrolledExpanded;
  const preview: MergePreview | null | undefined = row.merge_preview;
  const companyName = str(row.normalized_data_json.company_name as string | undefined);

  const toggleExpanded = () => {
    const next = !expanded;
    if (isControlled) {
      onExpandedChange?.(next);
      return;
    }
    setUncontrolledExpanded(next);
  };

  if (!preview?.groups?.length) {
    return (
      <div className="merge-diff-row">
        <button type="button" className="merge-diff-toggle" onClick={toggleExpanded}>
          <strong>{companyName}</strong>
          <span className="text-muted"> — Birleştirme önizlemesi yok</span>
        </button>
      </div>
    );
  }

  return (
    <div className="merge-diff-row">
      <button type="button" className="merge-diff-toggle" onClick={toggleExpanded}>
        <span className="merge-diff-chevron">{expanded ? "▼" : "▶"}</span>
        <strong>{companyName}</strong>
      </button>
      {expanded && (
        <div className="merge-diff-body">
          {preview.summary_lines.length > 0 && (
            <div className="merge-summary">
              <h4>Bu işlem sonucunda:</h4>
              <ul>
                {preview.summary_lines.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          {sortMergeGroups(preview.groups).map((group) => (
            <div key={group.entity} className="merge-entity-group">
              <h4>{mergeEntityLabels[group.entity] ?? group.entity_label}</h4>
              <table className="merge-diff-table">
                <thead>
                  <tr>
                    <th>Alan</th>
                    <th>CRM</th>
                    <th>Import</th>
                    <th>Sonuç</th>
                  </tr>
                </thead>
                <tbody>
                  {group.fields.map((field: MergeFieldPreview) => (
                    <tr key={field.field_key}>
                      <td>{field.label}</td>
                      <td>{str(field.crm_value)}</td>
                      <td>{str(field.import_value)}</td>
                      <td>
                        <OutcomeBadge outcome={field.outcome} label={field.outcome_label} />
                        {field.result_value && field.outcome !== "same" && field.outcome !== "empty" && (
                          <div className="merge-result-value text-muted">{str(field.result_value)}</div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function OutcomeBadge({ outcome, label }: { outcome: MergeOutcome; label: string }) {
  return (
    <Badge variant={mergeOutcomeBadgeVariant(outcome)}>
      {mergeOutcomeLabels[outcome] ?? label}
    </Badge>
  );
}
