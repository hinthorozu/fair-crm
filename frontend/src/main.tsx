import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { clearSession } from "./auth/session";
import { isSecuritySettingsPath, SecuritySettingsPage } from "./auth/SecuritySettingsPage";
import { isPublicAuthPath, PublicAuthRouter } from "./pages/PublicAuthPages";

const publicAuth = isPublicAuthPath(window.location.pathname);
const securitySettings = isSecuritySettingsPath(window.location.pathname);

function SecuritySettingsRoute() {
  const { session, isAuthenticated } = useAuth();
  const accessToken = session?.accessToken?.trim() ?? "";

  React.useEffect(() => {
    if (isAuthenticated && accessToken) return;
    window.location.replace("/login");
  }, [accessToken, isAuthenticated]);

  if (!isAuthenticated || !accessToken) return null;

  return (
    <SecuritySettingsPage
      accessToken={accessToken}
      onPasswordChanged={() => {
        clearSession();
        window.location.replace("/login");
      }}
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {publicAuth ? (
      <PublicAuthRouter />
    ) : (
      <AuthProvider>
        {securitySettings ? <SecuritySettingsRoute /> : <App />}
      </AuthProvider>
    )}
  </React.StrictMode>,
);
