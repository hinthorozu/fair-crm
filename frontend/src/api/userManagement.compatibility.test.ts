import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../auth/session", () => ({
  getAccessToken: vi.fn(() => "super-admin-access-token"),
  getOrganizationId: vi.fn(() => "actor-organization"),
}));

vi.mock("./client", () => {
  class MockApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public body?: unknown,
    ) {
      super(message);
      this.name = "ApiError";
    }
  }

  return {
    ApiError: MockApiError,
    fetchWithTimeout: vi.fn(),
  };
});

import { createManagedUser } from "./userManagement";
import { fetchWithTimeout } from "./client";

const mockedFetch = vi.mocked(fetchWithTimeout);

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("P0.2 Super Admin manual user-management compatibility", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it("keeps manual create on the existing Core users/manual endpoint with admin-supplied password", async () => {
    mockedFetch.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "user-1",
        email: "operator-created@example.com",
        organization_id: "organization-1",
        status: "active",
        role: null,
        is_super_admin: false,
      }),
    );

    await createManagedUser("organization-1", {
      email: "operator-created@example.com",
      password: "Admin-Supplied-Password-123",
      role_id: "role-1",
      status: "active",
    });

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const [url, options, timeout] = mockedFetch.mock.calls[0];
    expect(String(url)).toContain("/api/v1/organizations/organization-1/users/manual");
    expect(options?.method).toBe("POST");
    expect(timeout).toBe(15_000);

    const headers = options?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer super-admin-access-token");
    expect(headers.get("X-Organization-Id")).toBe("organization-1");
    expect(JSON.parse(String(options?.body))).toEqual({
      email: "operator-created@example.com",
      password: "Admin-Supplied-Password-123",
      role_id: "role-1",
      status: "active",
    });
  });

  it("does not invent a setup-link mode or Super Admin flag in the manual transport", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, { id: "user-2" }));

    await createManagedUser("organization-1", {
      email: "normal@example.com",
      password: "Manual-Password-456",
      role_id: "role-2",
      status: "inactive",
    });

    const [, options] = mockedFetch.mock.calls[0];
    const payload = JSON.parse(String(options?.body)) as Record<string, unknown>;
    expect(payload.password).toBe("Manual-Password-456");
    expect(payload).not.toHaveProperty("send_setup_link");
    expect(payload).not.toHaveProperty("setup_link");
    expect(payload).not.toHaveProperty("is_super_admin");
  });
});
