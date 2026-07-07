import { afterEach, describe, expect, it } from "vitest";
import {
  clearSession,
  getAccessToken,
  isAuthenticated,
  readSession,
  saveSession,
} from "./session";

const STORAGE_KEY = "fair-crm.auth.session";

describe("auth session", () => {
  afterEach(() => {
    window.localStorage.removeItem(STORAGE_KEY);
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
