import React from "react";
import { Badge } from "../../components/ui/Badge";
import { DetailWebsite } from "../../components/ui/DetailFields";
import { UniversalDataTable, type UniversalDataTableColumn } from "../../components/ui/UniversalDataTable";
import type { ImportRow, MergeFieldPreview, MergeOutcome, MergePreview } from "../../types/import";
import { mergeEntityLabels, mergeFieldSourceLabel, mergeOutcomeLabels } from "../../labels/importLabels";
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

function contactSummaryLine(preview: MergePreview): string | null {
  const contactGroup = preview.groups.find((group) => group.entity === "contact");
  if (!contactGroup?.fields.length) {
    return null;
  }
  const byKey = Object.fromEntries(contactGroup.fields.map((field) => [field.field_key, field]));
  const name = byKey.contact_name?.import_value ?? byKey.contact_name?.crm_value;
  const email = byKey.contact_email?.import_value ?? byKey.contact_email?.crm_value;
  const phone =
    byKey.contact_phone?.import_value ??
    byKey.contact_mobile_phone?.import_value ??
    byKey.contact_phone?.crm_value ??
    byKey.contact_mobile_phone?.crm_value;
  const parts = [name, email, phone].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : null;
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
  const contactSummary = preview ? contactSummaryLine(preview) : null;

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
        <span className="merge-diff-toggle-text">
          <strong>{companyName}</strong>
          {contactSummary ? (
            <span className="merge-contact-summary text-muted">Yetkili: {contactSummary}</span>
          ) : null}
        </span>
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
          {preview.contact_warnings && preview.contact_warnings.length > 0 ? (
            <ul className="merge-contact-warnings">
              {preview.contact_warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
          {sortMergeGroups(preview.groups).map((group) => (
            <MergeGroupTable
              key={group.entity}
              title={mergeEntityLabels[group.entity] ?? group.entity_label}
              fields={group.fields}
            />
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

function MergeGroupTable({ title, fields }: { title: string; fields: MergeFieldPreview[] }) {
  const columns = React.useMemo<UniversalDataTableColumn<MergeFieldPreview>[]>(
    () => [
      {
        key: "label",
        title: "Alan",
        sortable: false,
        allowWrap: true,
        render: (field) => field.label,
      },
      {
        key: "crm_value",
        title: "CRM",
        sortable: false,
        allowWrap: true,
        render: (field) => str(field.crm_value),
      },
      {
        key: "import_value",
        title: "Import",
        sortable: false,
        allowWrap: true,
        render: (field) => (
          <>
            <div>{str(field.import_value)}</div>
            {field.source_url ? (
              <div className="merge-field-source text-muted">
                <span>{mergeFieldSourceLabel}: </span>
                <DetailWebsite value={field.source_url} />
              </div>
            ) : null}
          </>
        ),
      },
      {
        key: "outcome",
        title: "Sonuç",
        sortable: false,
        allowWrap: true,
        render: (field) => (
          <>
            <OutcomeBadge outcome={field.outcome} label={field.outcome_label} />
            {field.result_value && field.outcome !== "same" && field.outcome !== "empty" ? (
              <div className="merge-result-value text-muted">{str(field.result_value)}</div>
            ) : null}
          </>
        ),
      },
    ],
    [],
  );

  return (
    <div className="merge-entity-group">
      <h4>{title}</h4>
      <UniversalDataTable
        items={fields}
        columns={columns}
        rowKey={(field) => field.field_key}
        className="merge-diff-table"
      />
    </div>
  );
}
