import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../auth/refreshCoordinator", () => ({
  refreshSessionSingleFlight: vi.fn(),
}));

vi.mock("../config", () => ({
  config: {
    apiBaseUrl: "",
    coreBaseUrl: "/kyrox-core",
    appEnv: "test",
    devBypassEnabled: false,
    devBypassToken: "dev-bypass",
    organizationId: "00000000-0000-4000-8000-000000000010",
  },
  buildApiHeaders: (extra: HeadersInit = {}) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const raw = window.localStorage.getItem("fair-crm.auth.session");
    if (raw) {
      const parsed = JSON.parse(raw) as { accessToken?: string };
      if (parsed.accessToken) {
        headers.Authorization = `Bearer ${parsed.accessToken}`;
        headers["X-Organization-Id"] = "00000000-0000-4000-8000-000000000010";
      }
    }
    return { ...headers, ...(extra as Record<string, string>) };
  },
}));

import { apiRequest } from "./client";
import { refreshSessionSingleFlight } from "../auth/refreshCoordinator";
import { clearSession, saveSession } from "../auth/session";

const mockedRefresh = vi.mocked(refreshSessionSingleFlight);

function installLocalStorage(): void {
  const store = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => store.clear(),
  };
  (globalThis as { window?: unknown }).window = {
    localStorage,
    dispatchEvent: () => true,
    setTimeout: globalThis.setTimeout.bind(globalThis),
    clearTimeout: globalThis.clearTimeout.bind(globalThis),
  };
  (globalThis as { localStorage?: unknown }).localStorage = localStorage;
}

describe("apiRequest refresh retry", () => {
  beforeEach(() => {
    installLocalStorage();
    clearSession();
    mockedRefresh.mockReset();
    saveSession({
      accessToken: "expired-access",
      organizationId: "00000000-0000-4000-8000-000000000010",
    });
  });

  afterEach(() => {
    clearSession();
    vi.unstubAllGlobals();
  });

  it("refreshes once then retries the original request on 401", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    mockedRefresh.mockImplementation(async () => {
      saveSession({
        accessToken: "fresh-access",
        organizationId: "00000000-0000-4000-8000-000000000010",
      });
      return "fresh-access";
    });

    const result = await apiRequest<{ ok: boolean }>("/api/v1/customers");
    expect(result).toEqual({ ok: true });
    expect(mockedRefresh).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
