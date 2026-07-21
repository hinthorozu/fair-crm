import React from "react";
import { CustomerTable } from "../components/CustomerList";
import { FairTable } from "../components/FairList";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import type { Customer } from "../types/customer";
import type { Fair } from "../types/fair";
import type { ServerDataTableController } from "../hooks/useServerDataTable";
import type { SortDirection } from "../types/listTable";

function mockCustomer(partial: Partial<Customer> & Pick<Customer, "id" | "display_name">): Customer {
  return {
    organization_id: "00000000-0000-4000-8000-000000000010",
    legal_name: partial.display_name,
    trade_name: null,
    normalized_name: partial.display_name.toLowerCase(),
    customer_type: "exhibitor",
    status: "active",
    website: null,
    phone: null,
    email: null,
    tax_number: null,
    tax_office: null,
    country: "TR",
    city: null,
    district: null,
    address: null,
    description: null,
    instagram_url: null,
    facebook_url: null,
    linkedin_url: null,
    youtube_url: null,
    source: "manual",
    email_allowed: true,
    sms_allowed: true,
    email_unsubscribed_at: null,
    sms_unsubscribed_at: null,
    consent_note: null,
    created_at: "2026-01-12T10:15:00Z",
    updated_at: "2026-06-01T14:22:00Z",
    deleted_at: null,
    phone_extra_count: 0,
    email_extra_count: 0,
    ...partial,
  };
}

function mockFair(partial: Partial<Fair> & Pick<Fair, "id" | "name">): Fair {
  const { id, name, ...rest } = partial;
  return {
    id,
    organization_id: "00000000-0000-4000-8000-000000000010",
    name,
    organizer: null,
    venue: null,
    city: "İstanbul",
    country: "TR",
    start_date: "2026-09-01",
    end_date: "2026-09-05",
    website: null,
    status: "planned",
    description: null,
    adapter_key: null,
    source_url: null,
    scraper_config: null,
    normalized_name: name.toLowerCase(),
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    deleted_at: null,
    ...rest,
  };
}

type TodoSmoke = {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_at: string;
  assignee: string;
  run_id: string;
};

type ImportSmoke = {
  id: string;
  fair_name: string;
  status: string;
  source: string;
  created_at: string;
  adapter_key: string;
};

type BackupSmoke = {
  id: string;
  name: string;
  status: string;
  created_at: string;
  size: string;
  job_id: string;
};

const MOCK_CUSTOMERS: Customer[] = [
  mockCustomer({
    id: "c1",
    display_name: "ACARLAR VAGON SAN. VE TİC. A.Ş.",
    city: "İstanbul",
    phone: "+90 212 555 0101",
    email: "info@acarlar-vagon.example",
  }),
  mockCustomer({
    id: "c2",
    display_name: "AKM ALARM KONTROL MERKEZİ A.Ş.",
    city: "Ankara",
    phone: "+90 312 555 0202",
    email: "satis@akm-alarm.example",
    phone_extra_count: 1,
  }),
  mockCustomer({
    id: "c3",
    display_name: "OMEGA TEXTILE MACHINERY LTD",
    city: "Bursa",
    phone: "+90 224 555 0303",
    email: "contact@omega-textile.example",
  }),
];

const MOCK_FAIRS: Fair[] = [
  mockFair({ id: "f1", name: "WIN Eurasia 2026", city: "İstanbul" }),
  mockFair({ id: "f2", name: "Ankara Endüstri Fuarı", city: "Ankara" }),
  mockFair({ id: "f3", name: "Bursa Makina Show", city: "Bursa", status: "completed" }),
];

const MOCK_TODOS: TodoSmoke[] = [
  {
    id: "t1",
    title: "Müşteri arama listesini güncelle",
    status: "open",
    priority: "high",
    due_at: "2026-07-22",
    assignee: "Ayşe",
    run_id: "run-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  },
  {
    id: "t2",
    title: "Takip notu ekle",
    status: "in_progress",
    priority: "medium",
    due_at: "2026-07-25",
    assignee: "Mehmet",
    run_id: "run-11111111-2222-3333-4444-555555555555",
  },
];

const MOCK_IMPORTS: ImportSmoke[] = [
  {
    id: "i1",
    fair_name: "WIN Eurasia 2026",
    status: "ready",
    source: "excel",
    created_at: "2026-07-10",
    adapter_key: "customer_contact_enrichment",
  },
  {
    id: "i2",
    fair_name: "Ankara Endüstri Fuarı",
    status: "applied",
    source: "scraper",
    created_at: "2026-07-08",
    adapter_key: "fair_participant_import",
  },
];

const MOCK_BACKUPS: BackupSmoke[] = [
  {
    id: "b1",
    name: "fair-crm-2026-07-21.dump",
    status: "completed",
    created_at: "2026-07-21 09:00",
    size: "128 MB",
    job_id: "job-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  },
  {
    id: "b2",
    name: "fair-crm-2026-07-20.dump",
    status: "completed",
    created_at: "2026-07-20 09:00",
    size: "126 MB",
    job_id: "job-11111111-2222-3333-4444-555555555555",
  },
];

function useSmokeSort(initial = "name") {
  const [sortField, setSortField] = React.useState(initial);
  const [sortDirection, setSortDirection] = React.useState<SortDirection>("asc");
  const onSortChange = React.useCallback(
    (field: string) => {
      if (field === sortField) {
        setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortDirection("asc");
      }
    },
    [sortField],
  );
  return { sortField, sortDirection, onSortChange };
}

function useSmokePaginationController<T>(items: T[]): ServerDataTableController<T> {
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(10);
  return React.useMemo(
    () =>
      ({
        items,
        loading: false,
        isRefreshing: false,
        error: null,
        search: "",
        setSearch: () => undefined,
        filters: {},
        setFilters: () => undefined,
        setFilter: () => undefined,
        filterCounts: {},
        responseFilters: {},
        sorting: { field: "name", direction: "asc" as const },
        setSort: () => undefined,
        setSorting: () => undefined,
        pagination: {
          page,
          pageSize,
          totalItems: 42,
          totalPages: Math.max(1, Math.ceil(42 / pageSize)),
        },
        setPage,
        setPageSize,
        refresh: async () => undefined,
        isEmpty: items.length === 0,
        hasActiveFilters: false,
      }) as unknown as ServerDataTableController<T>,
    [items, page, pageSize],
  );
}

const todoColumns: UniversalDataTableColumn<TodoSmoke>[] = [
  { key: "title", title: "Başlık", allowWrap: true, render: (r) => r.title },
  { key: "status", title: "Durum", render: (r) => r.status },
  { key: "priority", title: "Öncelik", render: (r) => r.priority },
  { key: "due_at", title: "Bitiş", render: (r) => r.due_at },
  { key: "assignee", title: "Atanan", render: (r) => r.assignee },
  {
    key: "run_id",
    title: "Çalışma Kimliği",
    priority: "technical",
    render: (r) => r.run_id,
  },
];

const importColumns: UniversalDataTableColumn<ImportSmoke>[] = [
  { key: "fair_name", title: "Fuar", allowWrap: true, render: (r) => r.fair_name },
  { key: "status", title: "Durum", render: (r) => r.status },
  { key: "source", title: "Kaynak", render: (r) => r.source },
  { key: "created_at", title: "Oluşturma", render: (r) => r.created_at },
  {
    key: "adapter_key",
    title: "Müşteri İletişim Zenginleştirme",
    dataLabel: "Adaptör",
    priority: "technical",
    render: (r) => r.adapter_key,
  },
];

const backupColumns: UniversalDataTableColumn<BackupSmoke>[] = [
  { key: "name", title: "Yedek", allowWrap: true, render: (r) => r.name },
  { key: "status", title: "Durum", render: (r) => r.status },
  { key: "created_at", title: "Tarih", render: (r) => r.created_at },
  { key: "size", title: "Boyut", render: (r) => r.size },
  {
    key: "job_id",
    title: "İş Kimliği",
    priority: "technical",
    render: (r) => r.job_id,
  },
];

type TabId = "customers" | "fairs" | "todos" | "imports" | "admin";

function tabFromSearch(): TabId {
  const raw = new URLSearchParams(window.location.search).get("tab");
  if (raw === "fairs" || raw === "todos" || raw === "imports" || raw === "admin") return raw;
  return "customers";
}

/**
 * DEV harness: project-wide table standard smoke (no auth).
 * Uses the same UniversalDataTable / ServerDataTableFrame stack as production lists.
 * Optional `?tab=customers|fairs|todos|imports|admin`.
 */
export function TableStandardSmokePage() {
  const [tab, setTab] = React.useState<TabId>(() => tabFromSearch());
  const customerSort = useSmokeSort("name");
  const fairSort = useSmokeSort("name");
  const todoTable = useSmokePaginationController(MOCK_TODOS);
  const importTable = useSmokePaginationController(MOCK_IMPORTS);
  const backupTable = useSmokePaginationController(MOCK_BACKUPS);

  const selectTab = React.useCallback((next: TabId) => {
    setTab(next);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.replaceState(null, "", `${url.pathname}${url.search}`);
  }, []);

  return (
    <div className="page" style={{ padding: "1rem" }} data-testid="table-standard-smoke">
      <h1>Table standard smoke</h1>
      <p className="muted">
        DEV — <code>UniversalDataTable</code> → <code>WidthResponsiveDataTable</code> + dual pagination.
        Same stack as production list screens.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        {(
          [
            ["customers", "Customers"],
            ["fairs", "Fairs"],
            ["todos", "Todos"],
            ["imports", "Imports"],
            ["admin", "Admin backups"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "btn primary" : "btn secondary"}
            onClick={() => selectTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "customers" ? (
        <CustomerTable
          items={MOCK_CUSTOMERS}
          archivingId={null}
          restoringId={null}
          sortField={customerSort.sortField}
          sortDirection={customerSort.sortDirection}
          onSortChange={customerSort.onSortChange}
          onEdit={() => undefined}
          onArchive={() => undefined}
          onRestore={() => undefined}
        />
      ) : null}

      {tab === "fairs" ? (
        <FairTable
          items={MOCK_FAIRS}
          archivingId={null}
          restoringId={null}
          sortField={fairSort.sortField}
          sortDirection={fairSort.sortDirection}
          onSortChange={fairSort.onSortChange}
          onEdit={() => undefined}
          onArchive={() => undefined}
          onRestore={() => undefined}
        />
      ) : null}

      {tab === "todos" ? (
        <UniversalDataTable table={todoTable} columns={todoColumns} rowKey={(r) => r.id} />
      ) : null}

      {tab === "imports" ? (
        <UniversalDataTable table={importTable} columns={importColumns} rowKey={(r) => r.id} />
      ) : null}

      {tab === "admin" ? (
        <UniversalDataTable table={backupTable} columns={backupColumns} rowKey={(r) => r.id} />
      ) : null}

      {/* Explicit dual-pagination frame demo when nested items-only tables lack outer frame */}
      {tab === "customers" || tab === "fairs" ? (
        <div style={{ marginTop: "1.5rem" }}>
          <h2>Dual pagination frame</h2>
          <ServerDataTableFrame table={todoTable} showPagination>
            <p className="muted">Shared top+bottom PaginationBar (same controller).</p>
          </ServerDataTableFrame>
        </div>
      ) : null}
    </div>
  );
}
