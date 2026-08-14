import React from "react";
import { loginWithCredentials, logoutSession } from "../api/auth";
import { config } from "../config";
import { fetchGrantedCorePermissions } from "../permissions/corePermissions";
import { refreshSessionSingleFlight } from "./refreshCoordinator";
import {
  clearSession,
  consumeLegacyRefreshTokenFromStorage,
  readSession,
  saveSession,
  SESSION_EXPIRED_EVENT,
  SESSION_UPDATED_EVENT,
  type AuthSession,
} from "./session";

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

async function withCorePermissions(session: AuthSession): Promise<AuthSession> {
  const permissions = await fetchGrantedCorePermissions(
    config.coreBaseUrl,
    session.accessToken,
    session.organizationId,
  );
  return { ...session, permissions };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = React.useState<AuthSession | null>(() => readSession());

  const logout = React.useCallback(async () => {
    clearSession();
    setSession(null);
    await logoutSession();
  }, []);

  const login = React.useCallback(async (email: string, password: string) => {
    const response = await loginWithCredentials({ email, password });
    const nextSession = await withCorePermissions({
      accessToken: response.access_token,
      organizationId: config.organizationId,
      email: email.trim(),
      expiresIn: response.expires_in,
    });
    saveSession(nextSession);
    setSession(nextSession);
  }, []);

  React.useEffect(() => {
    const onSessionExpired = () => {
      void logout();
      if (config.devBypassEnabled) return;
      if (window.location.pathname !== "/login") {
        window.history.replaceState(null, "", "/login");
      }
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [logout]);

  React.useEffect(() => {
    const onUpdated = () => setSession(readSession());
    window.addEventListener(SESSION_UPDATED_EVENT, onUpdated);
    return () => window.removeEventListener(SESSION_UPDATED_EVENT, onUpdated);
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      if (config.devBypassEnabled && !readSession()) return;
      const legacy = consumeLegacyRefreshTokenFromStorage();
      const current = readSession();
      if (current?.accessToken && !legacy) {
        try {
          const refreshed = await withCorePermissions(current);
          if (cancelled) return;
          saveSession(refreshed);
          setSession(refreshed);
        } catch {
          if (!cancelled) setSession(current);
        }
        return;
      }
      if (!current?.accessToken && !legacy) {
        if (window.location.pathname === "/login") return;
        const token = await refreshSessionSingleFlight({ silent: true });
        if (cancelled) return;
        if (token) setSession(readSession());
        return;
      }
      const token = await refreshSessionSingleFlight({
        legacyRefreshToken: legacy,
        silent: true,
      });
      if (cancelled) return;
      if (token) setSession(readSession());
      else if (current?.accessToken) setSession(current);
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null || config.devBypassEnabled,
      login,
      logout,
    }),
    [session, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
