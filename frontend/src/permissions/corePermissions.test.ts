import { afterEach, describe, expect, it, vi } from "vitest";
import {
  FAIR_CRM_PERMISSION_CODES,
  fetchGrantedCorePermissions,
} from "./corePermissions";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Core permission synchronization", () => {
  it("contains every permission code enforced by the Fair CRM backend and UI guards", () => {
    expect(new Set(FAIR_CRM_PERMISSION_CODES).size).toBe(FAIR_CRM_PERMISSION_CODES.length);
    expect(FAIR_CRM_PERMISSION_CODES).toHaveLength(96);
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.organizations.read");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.organizations.update");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.organizations.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.users.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.roles.create");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("identity.permissions.lifecycle");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.customers.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.customers.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.fairs.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.todos.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.todos.outcomes.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.imports.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.scraper.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.mail_templates.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.fair_emails.read");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.fair_emails.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.admin.backups.delete");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.admin.backups.execute");
    expect(FAIR_CRM_PERMISSION_CODES).toContain("fair_crm.admin.data_operations.execute");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.dashboard.read");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.imports.apply");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.scraper.run");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.scraper.download");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.mail_templates.render");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.mail_templates.test_send");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.fair_emails.preview");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.fair_emails.send");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.admin.backups.download");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain("fair_crm.admin.data_operations.run");
  });

  it("asks Core about every known permission and keeps only allowed results", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body)) as { permission_code: string };
      return new Response(
        JSON.stringify({ allowed: body.permission_code.endsWith(".read") }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const granted = await fetchGrantedCorePermissions(
      "http://core.test",
      "access-token",
      "organization-id",
    );

    expect(fetchMock).toHaveBeenCalledTimes(FAIR_CRM_PERMISSION_CODES.length);
    expect(granted.length).toBeGreaterThan(0);
    expect(granted.every((permissionCode) => permissionCode.endsWith(".read"))).toBe(true);
  });

  it("does not turn a denied Core result into a local grant", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ allowed: false }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      fetchGrantedCorePermissions("http://core.test", "access-token", "organization-id"),
    ).resolves.toEqual([]);
  });
});
