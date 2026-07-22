import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetRefreshCoordinatorForTests, refreshSessionSingleFlight } from "./refreshCoordinator";
import { clearSession, saveSession } from "./session";

vi.mock("../api/auth", () => ({
  refreshAccessToken: vi.fn(),
}));

import { refreshAccessToken } from "../api/auth";

const mockedRefresh = vi.mocked(refreshAccessToken);

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
  };
  (globalThis as { localStorage?: unknown }).localStorage = localStorage;
}

describe("refreshSessionSingleFlight", () => {
  beforeEach(() => {
    installLocalStorage();
    resetRefreshCoordinatorForTests();
    clearSession();
    mockedRefresh.mockReset();
    saveSession({
      accessToken: "old-access",
      organizationId: "00000000-0000-4000-8000-000000000010",
    });
  });

  afterEach(() => {
    resetRefreshCoordinatorForTests();
    clearSession();
  });

  it("dedupes parallel refresh calls into a single network request", async () => {
    let resolveRefresh: (value: {
      access_token: string;
      expires_in: number;
    }) => void = () => undefined;
    mockedRefresh.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRefresh = resolve;
        }),
    );

    const p1 = refreshSessionSingleFlight();
    const p2 = refreshSessionSingleFlight();
    const p3 = refreshSessionSingleFlight();

    expect(mockedRefresh).toHaveBeenCalledTimes(1);

    resolveRefresh({ access_token: "new-access", expires_in: 900 });
    const tokens = await Promise.all([p1, p2, p3]);
    expect(tokens).toEqual(["new-access", "new-access", "new-access"]);
    expect(mockedRefresh).toHaveBeenCalledTimes(1);
  });

  it("returns null and clears session when refresh fails", async () => {
    mockedRefresh.mockRejectedValue(new Error("unauthorized"));
    const token = await refreshSessionSingleFlight({ silent: true });
    expect(token).toBeNull();
    expect(window.localStorage.getItem("fair-crm.auth.session")).toBeNull();
  });
});
