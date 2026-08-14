import { config } from "../config";
import { replaceGrantedPermissions } from "../permissions/corePermissions";

const STORAGE_KEY = "fair-crm.auth.session";

export interface AuthSession {
  accessToken: string;
  organizationId: string;
  email?: string;
  permissions?: string[];
  /** Access token lifetime from login/refresh (seconds). */
  expiresIn?: number;
}

type LegacyStoredSession = Partial<AuthSession> & { refreshToken?: string };

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export const SESSION_UPDATED_EVENT = "fair-crm:session-updated";

function notifySessionUpdated(): void {
  if (typeof window === "undefined") return;
  if (typeof window.dispatchEvent !== "function") return;
  window.dispatchEvent(new CustomEvent(SESSION_UPDATED_EVENT));
}

function normalizePermissions(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

export function readSession(): AuthSession | null {
  if (!canUseStorage()) return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    replaceGrantedPermissions([]);
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as LegacyStoredSession;
    if (!parsed.accessToken || !parsed.organizationId) {
      replaceGrantedPermissions([]);
      return null;
    }
    const permissions = normalizePermissions(parsed.permissions);
    replaceGrantedPermissions(permissions);
    return {
      accessToken: parsed.accessToken,
      organizationId: parsed.organizationId,
      email: parsed.email,
      permissions,
      expiresIn: parsed.expiresIn,
    };
  } catch {
    replaceGrantedPermissions([]);
    return null;
  }
}

/**
 * One-shot migration: read legacy refresh_token from old localStorage JSON in memory only.
 * Never persists refresh tokens to localStorage/sessionStorage.
 */
export function consumeLegacyRefreshTokenFromStorage(): string | undefined {
  if (!canUseStorage()) return undefined;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as LegacyStoredSession;
    const legacy = typeof parsed.refreshToken === "string" ? parsed.refreshToken.trim() : "";
    if (!legacy) return undefined;
    if (parsed.accessToken && parsed.organizationId) {
      saveSession({
        accessToken: parsed.accessToken,
        organizationId: parsed.organizationId,
        email: parsed.email,
        permissions: normalizePermissions(parsed.permissions),
        expiresIn: parsed.expiresIn,
      });
    } else {
      clearSession();
    }
    return legacy;
  } catch {
    return undefined;
  }
}

export function saveSession(session: AuthSession): void {
  if (!canUseStorage()) return;
  const permissions = normalizePermissions(session.permissions);
  const payload: AuthSession = {
    accessToken: session.accessToken,
    organizationId: session.organizationId,
    email: session.email,
    permissions,
    expiresIn: session.expiresIn,
  };
  replaceGrantedPermissions(permissions);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  notifySessionUpdated();
}

export function clearSession(): void {
  replaceGrantedPermissions([]);
  if (!canUseStorage()) return;
  window.localStorage.removeItem(STORAGE_KEY);
  notifySessionUpdated();
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
