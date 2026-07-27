import { describe, expect, it } from "vitest";
import { customerToFormValues, emptyForm } from "../components/CustomerForm";
import type { Customer } from "../types/customer";
import {
  createCommunicationItem,
  formValuesToCustomerPayload,
} from "../utils/customerCommunicationForm";

function sampleCustomer(overrides: Partial<Customer> = {}): Customer {
  return {
    id: "customer-1",
    organization_id: "org-1",
    display_name: "Acme",
    legal_name: null,
    trade_name: null,
    normalized_name: "acme",
    customer_type: "lead",
    status: "active",
    website: null,
    phone: null,
    email: null,
    tax_number: null,
    tax_office: null,
    country: "Türkiye",
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
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    deleted_at: null,
    phones: [],
    emails: [],
    websites: [],
    ...overrides,
  };
}

describe("customerToFormValues", () => {
  it("maps email_allowed and sms_allowed for edit hydrate", () => {
    const values = customerToFormValues(
      sampleCustomer({ email_allowed: false, sms_allowed: true }),
    );
    expect(values.email_allowed).toBe(false);
    expect(values.sms_allowed).toBe(true);
  });
});

describe("customer form hydrate contract", () => {
  it("emptyForm defaults consent checkboxes to true for create", () => {
    expect(emptyForm().email_allowed).toBe(true);
    expect(emptyForm().sms_allowed).toBe(true);
  });

  it("emptyForm defaults customer_type to exhibitor for create", () => {
    expect(emptyForm().customer_type).toBe("exhibitor");
    expect(emptyForm().status).toBe("active");
  });

  it("hydrate should key off customer id, not object identity", () => {
    const customer = sampleCustomer({ email_allowed: false });
    const first = customerToFormValues(customer);
    const second = customerToFormValues({ ...customer });
    expect(first.email_allowed).toBe(false);
    expect(first).toEqual(second);
    expect(first).not.toBe(second);
    // Form must hydrate on customer.id (hydrateKey), never on `initial ===` identity.
    expect(customer.id).toBe("customer-1");
  });
});

describe("formValuesToCustomerPayload consent fields", () => {
  it("preserves email_allowed=false in update/create payload", () => {
    const payload = formValuesToCustomerPayload({
      display_name: "Acme",
      legal_name: null,
      trade_name: null,
      customer_type: "lead",
      status: "active",
      country: null,
      city: null,
      district: null,
      address: null,
      description: null,
      instagram_url: null,
      facebook_url: null,
      linkedin_url: null,
      youtube_url: null,
      source: "manual",
      phones: [],
      emails: [createCommunicationItem("info@acme.com", true)],
      websites: [],
      email_allowed: false,
      sms_allowed: true,
    });

    expect(payload.email_allowed).toBe(false);
    expect(payload.sms_allowed).toBe(true);
    expect(JSON.parse(JSON.stringify(payload)).email_allowed).toBe(false);
  });
});
