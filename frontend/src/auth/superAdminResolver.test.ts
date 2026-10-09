import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveSessionIdentity, resolveSessionSuperAdmin } from "./superAdminResolver";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("resolveSessionSuperAdmin", () => {
  it("uses the authenticated Core identity context", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ is_super_admin: true, organizations: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(resolveSessionSuperAdmin("http://core.test", "jwt-token")).resolves.toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://core.test/api/v1/user-management/context",
      expect.objectContaining({
        method: "GET",
        headers: { Authorization: "Bearer jwt-token" },
      }),
    );
  });

  it("uses the user's own organization instead of a session default", async () => {
    const organizationId = "b056434b-7b10-4490-b451-39629698e206";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            is_super_admin: true,
            organization_id: organizationId,
            organizations: [{ id: organizationId, name: "Umaay Mimarlık", slug: "umaay" }],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(resolveSessionIdentity("http://core.test", "jwt-token")).resolves.toEqual({
      isSuperAdmin: true,
      organizationId,
      organizationName: "Umaay Mimarlık",
    });
  });

  it("rejects invalid identity payloads instead of inferring Super Admin", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ is_super_admin: "yes" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(resolveSessionSuperAdmin("http://core.test", "jwt-token")).rejects.toThrow(
      "invalid payload",
    );
  });
});
