import { describe, expect, it } from "vitest";
import type { EmailAccount } from "../types/smtp";
import {
  formatEmailAccountOptionLabel,
  resolveDefaultEmailAccountId,
  selectActiveEmailAccounts,
} from "./emailAccountSelection";

function account(overrides: Partial<EmailAccount> & Pick<EmailAccount, "id" | "name">): EmailAccount {
  return {
    organization_id: "org-1",
    from_email: "noreply@example.com",
    from_name: null,
    host: "smtp.example.com",
    port: 587,
    username: null,
    encryption_type: "starttls",
    is_default: false,
    is_active: true,
    password_set: true,
    max_delivery_attempts: 3,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("selectActiveEmailAccounts", () => {
  it("returns only active accounts", () => {
    const accounts = [
      account({ id: "a1", name: "Active", is_active: true }),
      account({ id: "a2", name: "Inactive", is_active: false }),
      account({ id: "a3", name: "Also Active", is_active: true }),
    ];

    expect(selectActiveEmailAccounts(accounts).map((item) => item.id)).toEqual(["a1", "a3"]);
  });
});

describe("resolveDefaultEmailAccountId", () => {
  it("prefers the default active account", () => {
    const active = [
      account({ id: "a1", name: "First" }),
      account({ id: "a2", name: "Default", is_default: true }),
    ];
    expect(resolveDefaultEmailAccountId(active)).toBe("a2");
  });

  it("falls back to the first active account", () => {
    const active = [
      account({ id: "a1", name: "First" }),
      account({ id: "a2", name: "Second" }),
    ];
    expect(resolveDefaultEmailAccountId(active)).toBe("a1");
  });

  it("returns empty string when there are no active accounts", () => {
    expect(resolveDefaultEmailAccountId([])).toBe("");
  });
});

describe("formatEmailAccountOptionLabel", () => {
  it("appends default badge for default accounts", () => {
    expect(
      formatEmailAccountOptionLabel(account({ id: "a1", name: "Primary", is_default: true })),
    ).toBe("Primary (Varsayılan)");
  });

  it("returns the name alone for non-default accounts", () => {
    expect(formatEmailAccountOptionLabel(account({ id: "a1", name: "Secondary" }))).toBe(
      "Secondary",
    );
  });
});
