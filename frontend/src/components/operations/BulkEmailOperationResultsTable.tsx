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
import { formatBulkEmailRecipientDisplay } from "../../utils/bulkEmailRecipientDisplay";
import { listBulkEmailOperationRecipients } from "../../api/bulkEmailOperation";

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

const PROVIDER_STATUS_FILTER_OPTIONS = [
  "accepted",
  "sent",
  "delivered",
  "opened",
  "clicked",
  "soft_bounced",
  "hard_bounced",
  "unsubscribed",
  "spam_complaint",
] as const;

export interface BulkEmailOperationResultsTableProps {
  operationId: string;
  /** Bumps when live operation counters change or failed rows are retried. */
  dataVersion: string;
}

/** Server-side search, filtering, and pagination for recipient results. */
export function BulkEmailOperationResultsTable({
  operationId,
  dataVersion,
}: BulkEmailOperationResultsTableProps) {
  const fetchFn = React.useCallback(async (params: ServerTableFetchParams) => {
    const response = await listBulkEmailOperationRecipients(operationId, {
      page: params.page,
      pageSize: params.pageSize,
      search: params.search.trim() || undefined,
      status: params.filters.status || undefined,
      providerStatus: params.filters.provider_status || undefined,
    });
    return {
      items: response.items,
      pagination: {
        page: response.page,
        pageSize: response.page_size,
        totalItems: response.total_items,
        totalPages: response.total_pages,
        hasNext: response.page < response.total_pages,
        hasPrevious: response.page > 1,
      },
      sorting: { field: "created_at", direction: "asc" },
      filters: params.filters,
    } satisfies StandardListResponse<BulkEmailOperationRecipientRow>;
  }, [operationId]);

  const table = useServerDataTable<BulkEmailOperationRecipientRow>({
    fetchFn,
    filterKeys: ["status", "provider_status"],
    defaultFilters: { status: "", provider_status: "" },
    pageSize: DEFAULT_PAGE_SIZE,
    urlSync: false,
    debounceMs: 200,
    enabled: true,
  });

  React.useEffect(() => {
    // Polling / dataVersion bumps must not reset page, search, filters, or show skeleton.
    void table.refresh({ silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataVersion]);

  const columns = React.useMemo<UniversalDataTableColumn<BulkEmailOperationRecipientRow>[]>(
    () => [
      {
        key: "recipient_name",
        title: operationLabels.bulkEmailColRecipient,
        sortable: false,
        allowWrap: true,
        render: (item) => formatBulkEmailRecipientDisplay(item),
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
        key: "external_message_id",
        title: operationLabels.bulkEmailColMessageId,
        sortable: false,
        allowWrap: true,
        render: (item) => item.external_message_id?.trim() || "—",
      },
      {
        key: "provider_status",
        title: operationLabels.bulkEmailColProviderStatus,
        sortable: false,
        render: (item) => item.provider_status?.trim() || "—",
      },
      {
        key: "updated_at",
        title: operationLabels.bulkEmailColUpdatedAt,
        sortable: false,
        render: (item) => formatFairEmailDateTime(item.updated_at),
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
  const providerStatusValue = (table.filters.provider_status ?? "") as string;

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
              {["queued", "sending", "sent", "failed", "cancelled"].map((status) => (
                <option key={status} value={status}>
                  {fairEmailOutboxStatusLabel(status)}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField
            label={operationLabels.bulkEmailRecipientsProviderStatusFilter}
            htmlFor="bulk-email-results-provider-status"
          >
            <SelectInput
              id="bulk-email-results-provider-status"
              value={providerStatusValue}
              onChange={(event) => table.setFilter("provider_status", event.target.value)}
              aria-label={operationLabels.bulkEmailRecipientsProviderStatusFilter}
            >
              <option value="">{operationLabels.bulkEmailRecipientsStatusAll}</option>
              {PROVIDER_STATUS_FILTER_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
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
