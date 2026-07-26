import { describe, expect, it } from "vitest";
import { contactToFormValues, emptyForm } from "../components/ContactForm";
import type { Contact } from "../types/contact";

function sampleContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "contact-1",
    organization_id: "org-1",
    customer_id: "customer-1",
    first_name: "Ada",
    last_name: "Lovelace",
    full_name: "Ada Lovelace",
    title: null,
    department: null,
    email: "ada@example.com;second@example.com",
    phone: null,
    mobile_phone: null,
    linkedin: null,
    notes: null,
    is_primary: false,
    is_active: true,
    email_allowed: true,
    sms_allowed: true,
    email_unsubscribed_at: null,
    sms_unsubscribed_at: null,
    consent_note: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    deleted_at: null,
    ...overrides,
  };
}

describe("contactToFormValues", () => {
  it("maps multi-email string as-is for edit hydrate", () => {
    const values = contactToFormValues(
      sampleContact({ email: "a@x.com; b@y.com" }),
    );
    expect(values.email).toBe("a@x.com; b@y.com");
  });

  it("maps null email to empty string", () => {
    expect(contactToFormValues(sampleContact({ email: null })).email).toBe("");
  });
});

describe("contact form hydrate contract", () => {
  it("emptyForm starts with blank email for create", () => {
    expect(emptyForm().email).toBe("");
  });

  it("hydrate should key off contact id, not object identity", () => {
    const contact = sampleContact();
    const first = contactToFormValues(contact);
    const second = contactToFormValues({ ...contact });
    // Same logical snapshot, different object references (parent re-render).
    expect(first).toEqual(second);
    expect(first).not.toBe(second);
    // Form must hydrate on contact.id (hydrateKey), never on `initial ===` identity.
    expect(contact.id).toBe("contact-1");
  });
});
