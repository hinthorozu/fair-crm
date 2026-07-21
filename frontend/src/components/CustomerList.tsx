import type { Customer, CustomerStatus, CustomerType } from "../types/customer";
import { customerStatusLabels, customerTypeLabels, labels } from "../labels";
import { uiLabels } from "../labels/uiLabels";
import { Badge } from "./ui/Badge";
import { EmptyState, EmptyStateIcon } from "./ui/EmptyState";
import { UniversalDataTable, type UniversalDataTableColumn } from "./ui/UniversalDataTable";
import { FilterPanel } from "./ui/FilterPanel";
import { customerStatusBadgeVariant } from "../utils/badges";
import { CommunicationListCell } from "./CommunicationListCell";
import type { SortDirection } from "../types/listTable";

interface CustomerFiltersProps {
  search: string;
  status: CustomerStatus | "";
  customerType: CustomerType | "";
  onSearchChange: (value: string) => void;
  onStatusChange: (value: CustomerStatus | "") => void;
  onTypeChange: (value: CustomerType | "") => void;
  onRefresh: () => void;
}

export function CustomerFilters({
  search,
  status,
  customerType,
  onSearchChange,
  onStatusChange,
  onTypeChange,
  onRefresh,
}: CustomerFiltersProps) {
  return (
    <FilterPanel
      actions={
        <button type="button" className="btn secondary" onClick={onRefresh}>
          {labels.refresh}
        </button>
      }
    >
      <input
        type="search"
        className="search-input"
        placeholder={uiLabels.searchCustomer}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        aria-label={uiLabels.searchCustomer}
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as CustomerStatus | "")}
        aria-label={labels.status}
      >
        <option value="">{labels.allStatuses}</option>
        {(["lead", "active", "inactive", "archived"] as CustomerStatus[]).map((s) => (
          <option key={s} value={s}>
            {customerStatusLabels[s]}
          </option>
        ))}
      </select>
      <select
        value={customerType}
        onChange={(e) => onTypeChange(e.target.value as CustomerType | "")}
        aria-label={labels.customer_type}
      >
        <option value="">{labels.allTypes}</option>
        {Object.entries(customerTypeLabels).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </FilterPanel>
  );
}

interface CustomerTableProps {
  items: Customer[];
  onEdit: (customer: Customer) => void;
  onArchive: (customer: Customer) => void;
  onRestore: (customer: Customer) => void;
  onOpenDetail?: (customer: Customer) => void;
  onCreate?: () => void;
  archivingId: string | null;
  restoringId: string | null;
  sortField?: string | null;
  sortDirection?: "asc" | "desc" | null;
  onSortChange?: (field: string) => void;
  emptyDueToFilters?: boolean;
}

function isArchivedCustomer(customer: Customer): boolean {
  return customer.status === "archived" || customer.deleted_at !== null;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildCustomerColumns(props: CustomerTableProps): UniversalDataTableColumn<Customer>[] {
  const { onEdit, onArchive, onRestore, onOpenDetail, archivingId, restoringId } = props;
  return [
    {
      key: "name",
      title: labels.display_name,
      sortable: true,
      render: (c) => (
        <>
          {onOpenDetail ? (
            <button type="button" className="btn link name-link" onClick={() => onOpenDetail(c)}>
              <strong>{c.display_name}</strong>
            </button>
          ) : (
            <strong>{c.display_name}</strong>
          )}
          {c.trade_name && <div className="muted">{c.trade_name}</div>}
        </>
      ),
    },
    {
      key: "city",
      title: labels.city,
      sortable: true,
      render: (c) => c.city ?? "—",
    },
    {
      key: "customer_type",
      title: labels.customer_type,
      sortable: true,
      render: (c) => customerTypeLabels[c.customer_type] ?? c.customer_type,
    },
    {
      key: "status",
      title: labels.status,
      sortable: true,
      render: (c) => (
        <Badge variant={customerStatusBadgeVariant(c.status)}>
          {customerStatusLabels[c.status] ?? c.status}
        </Badge>
      ),
    },
    {
      key: "phone",
      title: labels.phone,
      sortable: true,
      render: (c) => (
        <CommunicationListCell value={c.phone} extraCount={c.phone_extra_count ?? 0} />
      ),
    },
    {
      key: "email",
      title: labels.email,
      sortable: true,
      render: (c) => (
        <CommunicationListCell value={c.email} extraCount={c.email_extra_count ?? 0} />
      ),
    },
    {
      key: "created_at",
      title: labels.created_at,
      sortable: true,
      render: (c) => formatDateTime(c.created_at),
    },
    {
      key: "updated_at",
      title: labels.updated_at,
      sortable: true,
      render: (c) => formatDateTime(c.updated_at),
    },
    {
      key: "actions",
      title: labels.actions,
      sortable: false,
      className: "actions",
      render: (c) => {
        const isArchived = isArchivedCustomer(c);
        return (
          <>
            {isArchived && (
              <button
                type="button"
                className="btn link"
                disabled={restoringId === c.id}
                onClick={() => onRestore(c)}
              >
                {restoringId === c.id ? labels.loading : labels.restore}
              </button>
            )}
            {!isArchived && (
              <>
                <button type="button" className="btn link" onClick={() => onEdit(c)}>
                  {labels.edit}
                </button>
                <button
                  type="button"
                  className="btn link danger"
                  disabled={archivingId === c.id}
                  onClick={() => onArchive(c)}
                >
                  {archivingId === c.id ? labels.loading : labels.archive}
                </button>
              </>
            )}
          </>
        );
      },
    },
  ];
}

export function buildAnalysisCustomerColumns(
  columnTitles: {
    companyName: string;
    legalName: string;
    tradeName: string;
    customerType: string;
    status: string;
    phone: string;
    email: string;
    website: string;
    city: string;
    country: string;
    createdAt: string;
    updatedAt: string;
  },
): UniversalDataTableColumn<Customer>[] {
  return [
    {
      key: "name",
      title: columnTitles.companyName,
      sortable: true,
      render: (c) => <strong>{c.display_name}</strong>,
    },
    {
      key: "legal_name",
      title: columnTitles.legalName,
      sortable: true,
      render: (c) => c.legal_name ?? "—",
    },
    {
      key: "trade_name",
      title: columnTitles.tradeName,
      sortable: true,
      render: (c) => c.trade_name ?? "—",
    },
    {
      key: "customer_type",
      title: columnTitles.customerType,
      sortable: true,
      render: (c) => customerTypeLabels[c.customer_type] ?? c.customer_type,
    },
    {
      key: "status",
      title: columnTitles.status,
      sortable: true,
      render: (c) => (
        <Badge variant={customerStatusBadgeVariant(c.status)}>
          {customerStatusLabels[c.status] ?? c.status}
        </Badge>
      ),
    },
    {
      key: "phone",
      title: columnTitles.phone,
      sortable: true,
      render: (c) => c.phone ?? "—",
    },
    {
      key: "email",
      title: columnTitles.email,
      sortable: true,
      render: (c) => c.email ?? "—",
    },
    {
      key: "website",
      title: columnTitles.website,
      sortable: true,
      render: (c) => c.website ?? "—",
    },
    {
      key: "city",
      title: columnTitles.city,
      sortable: true,
      render: (c) => c.city ?? "—",
    },
    {
      key: "country",
      title: columnTitles.country,
      sortable: true,
      render: (c) => c.country ?? "—",
    },
    {
      key: "created_at",
      title: columnTitles.createdAt,
      sortable: true,
      render: (c) => formatDateTime(c.created_at),
    },
    {
      key: "updated_at",
      title: columnTitles.updatedAt,
      sortable: true,
      render: (c) => formatDateTime(c.updated_at),
    },
  ];
}

export interface DuplicateDatasetCustomerRow {
  id: string;
  display_name: string;
  legal_name: string | null;
  trade_name: string | null;
  customer_type: string;
  status: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
  group_key: string;
  group_by: string | null;
  fair_count: number;
  first_fair: string | null;
}

export function buildDuplicateCustomerColumns(
  columnTitles: {
    groupKey: string;
    groupBy: string;
    companyName: string;
    legalName: string;
    tradeName: string;
    status: string;
    phone: string;
    email: string;
    website: string;
    city: string;
    country: string;
    fairCount: string;
    firstFair: string;
    createdAt: string;
    updatedAt: string;
  },
): UniversalDataTableColumn<DuplicateDatasetCustomerRow>[] {
  return [
    {
      key: "group_key",
      title: columnTitles.groupKey,
      sortable: true,
      render: (row) => <code>{row.group_key}</code>,
    },
    {
      key: "group_by",
      title: columnTitles.groupBy,
      sortable: true,
      render: (row) => row.group_by ?? "—",
    },
    {
      key: "name",
      title: columnTitles.companyName,
      sortable: true,
      render: (row) => <strong>{row.display_name}</strong>,
    },
    {
      key: "legal_name",
      title: columnTitles.legalName,
      sortable: true,
      render: (row) => row.legal_name ?? "—",
    },
    {
      key: "trade_name",
      title: columnTitles.tradeName,
      sortable: true,
      render: (row) => row.trade_name ?? "—",
    },
    {
      key: "phone",
      title: columnTitles.phone,
      sortable: true,
      render: (row) => row.phone ?? "—",
    },
    {
      key: "email",
      title: columnTitles.email,
      sortable: true,
      render: (row) => row.email ?? "—",
    },
    {
      key: "website",
      title: columnTitles.website,
      sortable: true,
      render: (row) => row.website ?? "—",
    },
    {
      key: "city",
      title: columnTitles.city,
      sortable: true,
      render: (row) => row.city ?? "—",
    },
    {
      key: "country",
      title: columnTitles.country,
      sortable: true,
      render: (row) => row.country ?? "—",
    },
    {
      key: "fair_count",
      title: columnTitles.fairCount,
      sortable: true,
      render: (row) => String(row.fair_count),
    },
    {
      key: "first_fair",
      title: columnTitles.firstFair,
      sortable: true,
      render: (row) => row.first_fair ?? "—",
    },
    {
      key: "status",
      title: columnTitles.status,
      sortable: true,
      render: (row) => (
        <Badge variant={customerStatusBadgeVariant(row.status as CustomerStatus)}>
          {customerStatusLabels[row.status as CustomerStatus] ?? row.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      title: columnTitles.createdAt,
      sortable: true,
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "updated_at",
      title: columnTitles.updatedAt,
      sortable: true,
      render: (row) => formatDateTime(row.updated_at),
    },
  ];
}

export function CustomerTable(props: CustomerTableProps) {
  const { items, onCreate, sortField, sortDirection, onSortChange, emptyDueToFilters } = props;
  const columns = buildCustomerColumns(props).map((column) =>
    column.key === "name" ? { ...column, allowWrap: true } : column,
  );

  return (
    <UniversalDataTable
      items={items}
      columns={columns}
      rowKey={(c) => c.id}
      sorting={{
        field: sortField ?? null,
        direction: (sortDirection ?? null) as SortDirection | null,
      }}
      onSortChange={onSortChange}
      emptyState={
        <EmptyState
          icon={<EmptyStateIcon />}
          title={emptyDueToFilters ? uiLabels.emptySearchTitle : uiLabels.emptyCustomersTitle}
          description={
            emptyDueToFilters
              ? uiLabels.emptySearchDescription
              : uiLabels.emptyCustomersDescription
          }
          actionLabel={onCreate ? uiLabels.createNew : undefined}
          onAction={onCreate}
        />
      }
    />
  );
}

export { Modal } from "./ui/Modal";
