import React from "react";
import { loginWithCredentials, logoutFromCore } from "../api/auth";
import { config } from "../config";
import {
  clearSession,
  notifySessionExpired,
  readSession,
  saveSession,
  SESSION_EXPIRED_EVENT,
  type AuthSession,
} from "./session";

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = React.useState<AuthSession | null>(() => readSession());

  const logout = React.useCallback(async () => {
    const current = readSession();
    clearSession();
    setSession(null);
    if (current?.refreshToken) {
      await logoutFromCore(current.refreshToken);
    }
  }, []);

  const login = React.useCallback(async (email: string, password: string) => {
    const response = await loginWithCredentials({ email, password });
    const nextSession: AuthSession = {
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      organizationId: config.organizationId,
      email: email.trim(),
    };
    saveSession(nextSession);
    setSession(nextSession);
  }, []);

  React.useEffect(() => {
    const onSessionExpired = () => {
      logout();
      if (window.location.pathname !== "/login") {
        window.history.replaceState(null, "", "/login");
      }
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [logout]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
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
