import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { labels } from "./labels";
import { config } from "./config";
import "./styles.css";

type AppRoute = "/" | "/fairs" | "/customers/:id";

interface ParsedRoute {
  route: AppRoute;
  customerId?: string;
}

function parseRoute(pathname: string): ParsedRoute {
  if (pathname === "/fairs" || pathname.startsWith("/fairs/")) {
    return { route: "/fairs" };
  }
  const customerMatch = pathname.match(/^\/customers\/([^/]+)$/);
  if (customerMatch) {
    return { route: "/customers/:id", customerId: customerMatch[1] };
  }
  return { route: "/" };
}

function navigate(path: string) {
  if (window.location.pathname !== path) {
    window.history.pushState(null, "", path);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function App() {
  const [parsed, setParsed] = React.useState<ParsedRoute>(() =>
    parseRoute(window.location.pathname),
  );

  React.useEffect(() => {
    const onPopState = () => {
      setParsed(parseRoute(window.location.pathname));
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleNav = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    navigate(path);
    setParsed(parseRoute(path));
  };

  const goToCustomerDetail = (customerId: string) => {
    const path = `/customers/${customerId}`;
    navigate(path);
    setParsed(parseRoute(path));
  };

  const goToCustomers = () => {
    navigate("/");
    setParsed({ route: "/" });
  };

  const isCustomersActive = parsed.route === "/" || parsed.route === "/customers/:id";

  return (
    <div className="app">
      <nav className="topbar">
        <div className="topbar-left">
          <span className="brand">{labels.appTitle}</span>
          <div className="nav-links">
            <a
              href="/"
              className={isCustomersActive ? "nav-link active" : "nav-link"}
              onClick={(e) => handleNav("/", e)}
            >
              {labels.customers}
            </a>
            <a
              href="/fairs"
              className={parsed.route === "/fairs" ? "nav-link active" : "nav-link"}
              onClick={(e) => handleNav("/fairs", e)}
            >
              Fuarlar
            </a>
          </div>
        </div>
        <span className="env-badge">Dev bypass · {config.organizationId.slice(0, 8)}…</span>
      </nav>
      <main>
        {parsed.route === "/fairs" && <FairsPage />}
        {parsed.route === "/" && <CustomersPage onOpenDetail={goToCustomerDetail} />}
        {parsed.route === "/customers/:id" && parsed.customerId && (
          <CustomerDetailPage customerId={parsed.customerId} onBack={goToCustomers} />
        )}
      </main>
    </div>
  );
}

export default App;
