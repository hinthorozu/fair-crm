import React from "react";
import { CustomerTable } from "../components/CustomerList";
import type { Customer } from "../types/customer";
import { PageShell } from "../components/ui/PageShell";

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

/** DEV-only visual harness for Customers width-responsive pilot (no auth). */
const MOCK_CUSTOMERS: Customer[] = [
  mockCustomer({
    id: "c1",
    display_name: "ACARLAR VAGON SAN. VE TİC. A.Ş.",
    city: "İstanbul",
    phone: "+90 212 555 0101",
    email: "info@acarlar-vagon.example",
    customer_type: "exhibitor",
    status: "active",
  }),
  mockCustomer({
    id: "c2",
    display_name: "AKM ALARM KONTROL MERKEZİ A.Ş.",
    trade_name: "AKM Alarm",
    city: "Ankara",
    phone: "+90 312 555 0202",
    email: "satis@akm-alarm.example",
    customer_type: "lead",
    status: "lead",
    phone_extra_count: 1,
    created_at: "2025-11-03T08:00:00Z",
    updated_at: "2026-05-20T09:10:00Z",
  }),
  mockCustomer({
    id: "c3",
    display_name: "OMEGA TEXTILE MACHINERY LTD",
    city: "Bursa",
    phone: "+90 224 555 0303",
    email: "contact@omega-textile.example",
    created_at: "2024-08-18T12:30:00Z",
    updated_at: "2026-04-11T16:45:00Z",
  }),
];

export function CustomersResponsivePilotPage() {
  const [sortField, setSortField] = React.useState("name");
  const [sortDirection, setSortDirection] = React.useState<"asc" | "desc">("asc");

  return (
    <PageShell style={{ padding: "1rem" }}>
      <h1>Customers width-responsive pilot</h1>
      <p className="muted">
        DEV harness — identical <code>CustomerTable</code> /{" "}
        <code>UniversalDataTable</code> → <code>WidthResponsiveDataTable</code> as{" "}
        <code>/customers</code>.
      </p>
      <CustomerTable
        items={MOCK_CUSTOMERS}
        archivingId={null}
        restoringId={null}
        sortField={sortField}
        sortDirection={sortDirection}
        onSortChange={(field) => {
          if (field === sortField) {
            setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
          } else {
            setSortField(field);
            setSortDirection("asc");
          }
        }}
        onEdit={() => undefined}
        onArchive={() => undefined}
        onRestore={() => undefined}
      />
    </PageShell>
  );
}
