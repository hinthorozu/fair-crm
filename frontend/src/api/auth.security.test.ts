import { beforeEach, describe, expect, it, vi } from "vitest";

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

import { changePassword } from "./auth";
import { ApiError, fetchWithTimeout } from "./client";
import { authLabels } from "../labels/authLabels";

const mockedFetch = vi.mocked(fetchWithTimeout);

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("authenticated password change bridge API", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it("forwards current/new password with the authenticated Bearer token", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, { message: "ok" }));

    await changePassword(
      {
        current_password: "current-password",
        new_password: "new-password-value",
      },
      "access-token",
    );

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const [url, options, timeout] = mockedFetch.mock.calls[0];
    expect(String(url)).toContain("/api/v1/auth/password/change");
    expect(options?.method).toBe("POST");
    expect(options?.credentials).toBe("include");
    expect(options?.headers).toEqual({
      "Content-Type": "application/json",
      Authorization: "Bearer access-token",
    });
    expect(JSON.parse(String(options?.body))).toEqual({
      current_password: "current-password",
      new_password: "new-password-value",
    });
    expect(timeout).toBe(30_000);
  });

  it("fails closed without an access token and does not call the bridge", async () => {
    await expect(
      changePassword(
        { current_password: "current-password", new_password: "new-password-value" },
        "  ",
      ),
    ).rejects.toMatchObject<ApiError>({
      status: 401,
      message: authLabels.sessionRequired,
    });
    expect(mockedFetch).not.toHaveBeenCalled();
  });

  it("preserves safe Core 4xx detail for current-password/policy feedback", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(422, { detail: "Password must be at least 12 characters" }));

    await expect(
      changePassword(
        { current_password: "current-password", new_password: "short" },
        "access-token",
      ),
    ).rejects.toMatchObject<ApiError>({
      status: 422,
      message: "Password must be at least 12 characters",
    });
  });

  it("does not expose upstream 5xx detail", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(503, { detail: "core-provider-internal-secret" }));

    await expect(
      changePassword(
        { current_password: "current-password", new_password: "new-password-value" },
        "access-token",
      ),
    ).rejects.toMatchObject<ApiError>({
      status: 503,
      message: authLabels.networkError,
    });
  });

  it("fails closed on malformed success payload", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, { unexpected: true }));

    await expect(
      changePassword(
        { current_password: "current-password", new_password: "new-password-value" },
        "access-token",
      ),
    ).rejects.toMatchObject<ApiError>({
      status: 200,
      message: authLabels.requestFailed,
    });
  });
});
