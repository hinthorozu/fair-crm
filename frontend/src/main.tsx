import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { isPublicAuthPath, PublicAuthRouter } from "./pages/PublicAuthPages";

const publicAuth = isPublicAuthPath(window.location.pathname);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {publicAuth ? (
      <PublicAuthRouter />
    ) : (
      <AuthProvider>
        <App />
      </AuthProvider>
    )}
  </React.StrictMode>,
);
