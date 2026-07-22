import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearSession,
  getAccessToken,
  isAuthenticated,
  readSession,
  saveSession,
} from "./session";

const STORAGE_KEY = "fair-crm.auth.session";

/**
 * Vitest runs with environment: "node" (no DOM). Session storage APIs require
 * window.localStorage — install a minimal in-memory shim for these unit tests.
 */
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
    clear: () => {
      store.clear();
    },
  };
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    writable: true,
    value: {
      localStorage,
      dispatchEvent: () => true,
    },
  });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    writable: true,
    value: localStorage,
  });
  if (typeof globalThis.CustomEvent === "undefined") {
    Object.defineProperty(globalThis, "CustomEvent", {
      configurable: true,
      writable: true,
      value: class CustomEvent {
        type: string;
        constructor(type: string) {
          this.type = type;
        }
      },
    });
  }
}

function uninstallLocalStorage(): void {
  Reflect.deleteProperty(globalThis, "window");
  Reflect.deleteProperty(globalThis, "localStorage");
}

describe("auth session", () => {
  beforeEach(() => {
    installLocalStorage();
  });

  afterEach(() => {
    const win = (globalThis as { window?: { localStorage?: { removeItem: (key: string) => void } } })
      .window;
    win?.localStorage?.removeItem(STORAGE_KEY);
    uninstallLocalStorage();
  });

  it("persists and reads access token", () => {
    saveSession({
      accessToken: "jwt-token",
      organizationId: "00000000-0000-4000-8000-000000000010",
      email: "dev@example.com",
    });

    expect(isAuthenticated()).toBe(true);
    expect(getAccessToken()).toBe("jwt-token");
    expect(readSession()?.email).toBe("dev@example.com");
  });

  it("clears session on logout", () => {
    saveSession({
      accessToken: "jwt-token",
      organizationId: "00000000-0000-4000-8000-000000000010",
    });
    clearSession();
    expect(isAuthenticated()).toBe(false);
    expect(readSession()).toBeNull();
  });
});
