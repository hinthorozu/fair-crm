import React from "react";
import { EmptyState } from "../ui/EmptyState";
import { FilterPanel } from "../ui/FilterPanel";
import { FormField, SelectInput, TextInput } from "../ui/form";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../ui/UniversalDataTable";
import { useServerDataTable, type ServerTableFetchParams } from "../../hooks/useServerDataTable";
import { operationLabels } from "../../labels/operationLabels";
import { uiLabels } from "../../labels/uiLabels";
import type {
  BulkEmailOperationPreviewRecipient,
  BulkEmailOperationSourceType,
} from "../../types/bulkEmailOperation";
import type { StandardListResponse } from "../../types/listTable";
import { DEFAULT_PAGE_SIZE } from "../../types/listTable";

type StatusFilter = "" | "will_send" | "skip";

function skipReasonLabel(reason: string | null): string {
  switch (reason) {
    case "inactive_record":
      return operationLabels.bulkEmailSkipReasonInactive;
    case "no_email":
      return operationLabels.bulkEmailSkipReasonNoEmail;
    case "invalid_email":
      return operationLabels.bulkEmailSkipReasonInvalidEmail;
    case "duplicate_email":
      return operationLabels.bulkEmailSkipReasonDuplicate;
    default:
      return reason ?? "—";
  }
}

function sourceLabel(source: string, sourceType: BulkEmailOperationSourceType): string {
  if (sourceType === "manual") {
    if (source === "excel") return operationLabels.bulkEmailSourceExcelShort;
    return operationLabels.bulkEmailSourceManualShort;
  }
  if (source === "contact") return operationLabels.bulkEmailSourceContact;
  if (source === "customer") return operationLabels.bulkEmailSourceCompany;
  return source;
}

function matchesSearch(item: BulkEmailOperationPreviewRecipient, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = [
    item.recipient_name,
    item.company_name,
    item.email,
    item.fair_name,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function filterRecipients(
  recipients: BulkEmailOperationPreviewRecipient[],
  params: ServerTableFetchParams,
): BulkEmailOperationPreviewRecipient[] {
  const status = (params.filters.status ?? "") as StatusFilter;
  return recipients.filter((item) => {
    if (status === "will_send" && item.status !== "will_send") return false;
    if (status === "skip" && item.status !== "skip") return false;
    return matchesSearch(item, params.search);
  });
}

function toClientListResponse(
  items: BulkEmailOperationPreviewRecipient[],
  page: number,
  pageSize: number,
): StandardListResponse<BulkEmailOperationPreviewRecipient> {
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

export interface BulkEmailPreviewRecipientsTableProps {
  recipients: BulkEmailOperationPreviewRecipient[];
  sourceType: BulkEmailOperationSourceType;
  /** Changes when preview result is replaced; does not re-call preview API. */
  dataVersion: string;
}

/**
 * Client-side search / status filter / pagination over an already-fetched preview result.
 * Does not call the preview API.
 */
export function BulkEmailPreviewRecipientsTable({
  recipients,
  sourceType,
  dataVersion,
}: BulkEmailPreviewRecipientsTableProps) {
  const recipientsRef = React.useRef(recipients);
  recipientsRef.current = recipients;

  const fetchFn = React.useCallback(async (params: ServerTableFetchParams) => {
    const filtered = filterRecipients(recipientsRef.current, params);
    return toClientListResponse(filtered, params.page, params.pageSize);
  }, []);

  const table = useServerDataTable<BulkEmailOperationPreviewRecipient>({
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
    // Refresh only when the preview payload identity changes — not on filter/page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataVersion]);

  const columns = React.useMemo<UniversalDataTableColumn<BulkEmailOperationPreviewRecipient>[]>(
    () => [
      {
        key: "recipient_name",
        title: operationLabels.bulkEmailColRecipient,
        sortable: false,
        allowWrap: true,
        render: (item) => item.recipient_name ?? "—",
      },
      {
        key: "company_name",
        title: operationLabels.bulkEmailColCompany,
        sortable: false,
        allowWrap: true,
        render: (item) => item.company_name ?? "—",
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
        render: (item) => sourceLabel(item.source, sourceType),
      },
      {
        key: "fair_name",
        title: operationLabels.bulkEmailColFair,
        sortable: false,
        allowWrap: true,
        render: (item) => item.fair_name ?? "—",
      },
      {
        key: "status",
        title: operationLabels.bulkEmailColStatus,
        sortable: false,
        render: (item) =>
          item.status === "will_send"
            ? operationLabels.bulkEmailStatusWillSend
            : operationLabels.bulkEmailStatusSkip,
      },
      {
        key: "skip_reason",
        title: operationLabels.bulkEmailColSkipReason,
        sortable: false,
        allowWrap: true,
        render: (item) => skipReasonLabel(item.skip_reason),
      },
    ],
    [sourceType],
  );

  const statusValue = (table.filters.status ?? "") as StatusFilter;

  return (
    <UniversalDataTable
      table={table}
      columns={columns}
      rowKey={(item) => item.recipient_key}
      className="bulk-email-operation-recipients-table"
      toolbar={
        <FilterPanel ariaLabel={operationLabels.bulkEmailRecipientsFilterAria}>
          <FormField
            label={operationLabels.bulkEmailRecipientsSearchLabel}
            htmlFor="bulk-email-recipients-search"
            fullWidth
          >
            <TextInput
              id="bulk-email-recipients-search"
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
            htmlFor="bulk-email-recipients-status"
          >
            <SelectInput
              id="bulk-email-recipients-status"
              value={statusValue}
              onChange={(event) => table.setFilter("status", event.target.value)}
              aria-label={operationLabels.bulkEmailRecipientsStatusFilter}
            >
              <option value="">{operationLabels.bulkEmailRecipientsStatusAll}</option>
              <option value="will_send">{operationLabels.bulkEmailStatusWillSend}</option>
              <option value="skip">{operationLabels.bulkEmailStatusSkip}</option>
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
