import { config } from "../config";

const STORAGE_KEY = "fair-crm.auth.session";

export interface AuthSession {
  accessToken: string;
  refreshToken?: string;
  organizationId: string;
  email?: string;
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function readSession(): AuthSession | null {
  if (!canUseStorage()) return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (!parsed.accessToken || !parsed.organizationId) {
      return null;
    }
    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
      organizationId: parsed.organizationId,
      email: parsed.email,
    };
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return readSession()?.accessToken ?? null;
}

export function getOrganizationId(): string | null {
  return readSession()?.organizationId ?? config.organizationId;
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

export const SESSION_EXPIRED_EVENT = "fair-crm:session-expired";

export function notifySessionExpired(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
}
