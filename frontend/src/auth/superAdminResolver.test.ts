import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveSessionSuperAdmin } from "./superAdminResolver";

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
