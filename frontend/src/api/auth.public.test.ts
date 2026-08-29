import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./client", async () => {
  const actual = await vi.importActual<typeof import("./client")>("./client");
  return { ...actual, fetchWithTimeout: vi.fn() };
});

import {
  completeAccountActivation,
  requestPasswordReset,
  resetPassword,
  signupAccount,
} from "./auth";
import { ApiError, fetchWithTimeout } from "./client";
import { authLabels } from "../labels/authLabels";

const mockedFetch = vi.mocked(fetchWithTimeout);

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("public auth bridge API", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it.each([
    [
      "signup",
      () => signupAccount({ organization_name: "Acme", email: "owner@example.com" }),
      "/api/v1/auth/signup",
      { organization_name: "Acme", email: "owner@example.com" },
    ],
    [
      "activation",
      () => completeAccountActivation({ token: "activation-secret", password: "long-enough-password" }),
      "/api/v1/auth/activation/complete",
      { token: "activation-secret", password: "long-enough-password" },
    ],
    [
      "forgot password",
      () => requestPasswordReset({ email: "owner@example.com" }),
      "/api/v1/auth/password/forgot",
      { email: "owner@example.com" },
    ],
    [
      "reset password",
      () => resetPassword({ token: "reset-secret", password: "long-enough-password" }),
      "/api/v1/auth/password/reset",
      { token: "reset-secret", password: "long-enough-password" },
    ],
  ])("posts %s through the FAIR CRM bridge without auth/CSRF headers", async (_name, action, path, body) => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, { message: "ok" }));

    await action();

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const [url, options, timeout] = mockedFetch.mock.calls[0];
    expect(String(url)).toContain(path);
    expect(options?.method).toBe("POST");
    expect(options?.credentials).toBe("include");
    expect(options?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(options?.body))).toEqual(body);
    expect(timeout).toBe(30_000);
  });

  it("preserves safe Core 4xx detail for form feedback", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(422, { detail: "Password must be at least 12 characters" }));

    await expect(
      completeAccountActivation({ token: "token", password: "short" }),
    ).rejects.toMatchObject<ApiError>({
      status: 422,
      message: "Password must be at least 12 characters",
    });
  });

  it("does not expose upstream 5xx detail", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(503, { detail: "smtp-secret-provider-error" }));

    await expect(requestPasswordReset({ email: "owner@example.com" })).rejects.toMatchObject<ApiError>({
      status: 503,
      message: authLabels.networkError,
    });
  });

  it("fails closed on malformed success payload", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(202, { unexpected: true }));

    await expect(signupAccount({ organization_name: "Acme", email: "owner@example.com" })).rejects.toMatchObject<ApiError>({
      status: 202,
      message: authLabels.requestFailed,
    });
  });
});
