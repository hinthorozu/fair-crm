import React from "react";
import { EmptyState } from "../ui/EmptyState";
import { FilterPanel } from "../ui/FilterPanel";
import { FormField, SelectInput, TextInput } from "../ui/form";
import { Badge } from "../ui/Badge";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../ui/UniversalDataTable";
import { useServerDataTable, type ServerTableFetchParams } from "../../hooks/useServerDataTable";
import { operationLabels } from "../../labels/operationLabels";
import { uiLabels } from "../../labels/uiLabels";
import type { BulkEmailOperationRecipientRow } from "../../types/bulkEmailOperation";
import type { StandardListResponse } from "../../types/listTable";
import { DEFAULT_PAGE_SIZE } from "../../types/listTable";
import {
  fairEmailOutboxStatusLabel,
  fairEmailOutboxStatusVariant,
  formatFairEmailDateTime,
} from "../../utils/fairBulkEmailLogs";

function sourceLabel(source: string): string {
  if (source === "excel") return operationLabels.bulkEmailSourceExcelShort;
  if (source === "manual") return operationLabels.bulkEmailSourceManualShort;
  if (source === "contact") return operationLabels.bulkEmailSourceContact;
  if (source === "customer") return operationLabels.bulkEmailSourceCompany;
  return source || "—";
}

function formatRecipientError(message: string | null, status: string): string {
  if (!message && !status) return "—";
  const raw = message ?? "";
  const haystack = `${status} ${raw}`.toLowerCase();
  if (haystack.includes("sending_timeout")) {
    if (!raw) return operationLabels.bulkEmailSendingTimeoutHint;
    return `${raw} — ${operationLabels.bulkEmailSendingTimeoutHint}`;
  }
  return raw || "—";
}

function matchesSearch(item: BulkEmailOperationRecipientRow, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = [
    item.recipient_name,
    item.company_name,
    item.email,
    item.source,
    item.fair_name,
    item.status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function filterRecipients(
  recipients: BulkEmailOperationRecipientRow[],
  params: ServerTableFetchParams,
): BulkEmailOperationRecipientRow[] {
  const status = (params.filters.status ?? "").trim();
  return recipients.filter((item) => {
    if (status && item.status !== status) return false;
    return matchesSearch(item, params.search);
  });
}

function toClientListResponse(
  items: BulkEmailOperationRecipientRow[],
  page: number,
  pageSize: number,
): StandardListResponse<BulkEmailOperationRecipientRow> {
  const totalItems = items.length;
  const totalPages = totalItems === 0 ? 0 : Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = totalPages === 0 ? 1 : Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    pagination: {
      page: safePage,
      pageSize,
      totalItems,
      totalPages,
      hasNext: safePage < totalPages,
      hasPrevious: safePage > 1,
    },
    sorting: { field: "email", direction: "asc" },
    filters: {},
  };
}

export interface BulkEmailOperationResultsTableProps {
  recipients: BulkEmailOperationRecipientRow[];
  /** Bumps when recipient list is replaced (e.g. after poll/retry). */
  dataVersion: string;
}

/**
 * Client-side search / status filter / pagination over already-fetched recipient results.
 */
export function BulkEmailOperationResultsTable({
  recipients,
  dataVersion,
}: BulkEmailOperationResultsTableProps) {
  const recipientsRef = React.useRef(recipients);
  recipientsRef.current = recipients;

  const statusOptions = React.useMemo(() => {
    const set = new Set(recipients.map((item) => item.status).filter(Boolean));
    return Array.from(set).sort();
  }, [recipients]);

  const fetchFn = React.useCallback(async (params: ServerTableFetchParams) => {
    const filtered = filterRecipients(recipientsRef.current, params);
    return toClientListResponse(filtered, params.page, params.pageSize);
  }, []);

  const table = useServerDataTable<BulkEmailOperationRecipientRow>({
    fetchFn,
    filterKeys: ["status"],
    defaultFilters: { status: "" },
    pageSize: DEFAULT_PAGE_SIZE,
    urlSync: false,
    debounceMs: 200,
    enabled: true,
  });

  React.useEffect(() => {
    void table.refresh({ page: 1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataVersion]);

  const columns = React.useMemo<UniversalDataTableColumn<BulkEmailOperationRecipientRow>[]>(
    () => [
      {
        key: "recipient_name",
        title: operationLabels.bulkEmailColRecipient,
        sortable: false,
        allowWrap: true,
        render: (item) => item.recipient_name?.trim() || "—",
      },
      {
        key: "company_name",
        title: operationLabels.bulkEmailColCompany,
        sortable: false,
        allowWrap: true,
        render: (item) => item.company_name?.trim() || "—",
      },
      {
        key: "email",
        title: operationLabels.bulkEmailColEmail,
        sortable: false,
        allowWrap: true,
        render: (item) => item.email || "—",
      },
      {
        key: "source",
        title: operationLabels.bulkEmailColSource,
        sortable: false,
        render: (item) => sourceLabel(item.source),
      },
      {
        key: "fair",
        title: operationLabels.bulkEmailColFair,
        sortable: false,
        allowWrap: true,
        render: (item) => item.fair_name?.trim() || "—",
      },
      {
        key: "status",
        title: operationLabels.bulkEmailColStatus,
        sortable: false,
        render: (item) => (
          <Badge variant={fairEmailOutboxStatusVariant(item.status)}>
            {fairEmailOutboxStatusLabel(item.status)}
          </Badge>
        ),
      },
      {
        key: "error_message",
        title: operationLabels.bulkEmailColError,
        sortable: false,
        allowWrap: true,
        render: (item) => (
          <span className="error-cell">{formatRecipientError(item.error_message, item.status)}</span>
        ),
      },
      {
        key: "send_attempt",
        title: operationLabels.bulkEmailColAttempt,
        sortable: false,
        render: (item) => String(item.send_attempt ?? 0),
      },
      {
        key: "sent_at",
        title: operationLabels.bulkEmailColSentAt,
        sortable: false,
        render: (item) => formatFairEmailDateTime(item.sent_at),
      },
    ],
    [],
  );

  const statusValue = (table.filters.status ?? "") as string;

  return (
    <UniversalDataTable
      table={table}
      columns={columns}
      rowKey={(item) => item.id}
      className="bulk-email-operation-results-table"
      toolbar={
        <FilterPanel ariaLabel={operationLabels.bulkEmailRecipientsFilterAria}>
          <FormField
            label={operationLabels.bulkEmailRecipientsSearchLabel}
            htmlFor="bulk-email-results-search"
            fullWidth
          >
            <TextInput
              id="bulk-email-results-search"
              type="search"
              className="search-input"
              value={table.search}
              onChange={(event) => table.setSearch(event.target.value)}
              placeholder={operationLabels.bulkEmailRecipientsSearchPlaceholder}
              aria-label={operationLabels.bulkEmailRecipientsSearchPlaceholder}
            />
          </FormField>
          <FormField
            label={operationLabels.bulkEmailRecipientsStatusFilter}
            htmlFor="bulk-email-results-status"
          >
            <SelectInput
              id="bulk-email-results-status"
              value={statusValue}
              onChange={(event) => table.setFilter("status", event.target.value)}
              aria-label={operationLabels.bulkEmailRecipientsStatusFilter}
            >
              <option value="">{operationLabels.bulkEmailRecipientsStatusAll}</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {fairEmailOutboxStatusLabel(status)}
                </option>
              ))}
            </SelectInput>
          </FormField>
        </FilterPanel>
      }
      emptyState={
        <EmptyState
          title={
            table.hasActiveFilters
              ? uiLabels.emptySearchTitle
              : operationLabels.bulkEmailPreviewEmptyRecipients
          }
          description={
            table.hasActiveFilters
              ? operationLabels.bulkEmailRecipientsEmptyFiltered
              : undefined
          }
        />
      }
    />
  );
}
