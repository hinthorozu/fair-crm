import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { FairDetailPage } from "./pages/FairDetailPage";
import { ImportWizardPage } from "./pages/ImportWizardPage";
import { AppLayout } from "./components/layout/AppLayout";
import { uiLabels } from "./labels/uiLabels";
import { labels } from "./labels";
import "./styles.css";

type AppRoute =
  | "/customers"
  | "/fairs"
  | "/fairs/:id"
  | "/imports"
  | "/imports/fair/:fairId"
  | "/customers/:id";

interface ParsedRoute {
  route: AppRoute;
  customerId?: string;
  fairId?: string;
}

function parseRoute(pathname: string): ParsedRoute {
  if (pathname === "/imports" || pathname.startsWith("/imports/")) {
    const fairImport = pathname.match(/^\/imports\/fair\/([^/]+)$/);
    if (fairImport) {
      return { route: "/imports/fair/:fairId", fairId: fairImport[1] };
    }
    return { route: "/imports" };
  }
  if (pathname === "/fairs" || pathname.startsWith("/fairs/")) {
    const fairMatch = pathname.match(/^\/fairs\/([^/]+)$/);
    if (fairMatch) {
      return { route: "/fairs/:id", fairId: fairMatch[1] };
    }
    return { route: "/fairs" };
  }
  if (pathname === "/customers") {
    return { route: "/customers" };
  }
  const customerMatch = pathname.match(/^\/customers\/([^/]+)$/);
  if (customerMatch) {
    return { route: "/customers/:id", customerId: customerMatch[1] };
  }
  if (pathname === "/") {
    return { route: "/customers" };
  }
  return { route: "/customers" };
}

function splitPath(path: string): { pathname: string; search: string } {
  const queryIndex = path.indexOf("?");
  if (queryIndex === -1) {
    return { pathname: path, search: "" };
  }
  return {
    pathname: path.slice(0, queryIndex),
    search: path.slice(queryIndex),
  };
}

function navigate(path: string) {
  const { pathname, search } = splitPath(path);
  const nextSearch =
    search || (window.location.pathname === pathname ? window.location.search : "");
  const next = `${pathname}${nextSearch}`;
  if (`${window.location.pathname}${window.location.search}` !== next) {
    window.history.pushState(null, "", next);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function App() {
  const [parsed, setParsed] = React.useState<ParsedRoute>(() =>
    parseRoute(window.location.pathname),
  );
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [customerName, setCustomerName] = React.useState<string | null>(null);
  const [fairName, setFairName] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (window.location.pathname === "/") {
      const next = `/customers${window.location.search}`;
      window.history.replaceState(null, "", next);
      setParsed(parseRoute("/customers"));
    }
  }, []);

  React.useEffect(() => {
    const onPopState = () => {
      setParsed(parseRoute(window.location.pathname));
      setSidebarOpen(false);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleNav = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    const { pathname } = splitPath(path);
    navigate(pathname);
    setParsed(parseRoute(pathname));
    setSidebarOpen(false);
    if (pathname === "/customers") setCustomerName(null);
    if (pathname === "/fairs") setFairName(null);
  };

  const goToCustomerDetail = (customerId: string) => {
    const path = `/customers/${customerId}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToCustomers = () => {
    navigate("/customers");
    setParsed({ route: "/customers" });
    setCustomerName(null);
    setSidebarOpen(false);
  };

  const goToFairs = () => {
    navigate("/fairs");
    setParsed({ route: "/fairs" });
    setFairName(null);
    setSidebarOpen(false);
  };

  const goToImportWizard = (fairId?: string) => {
    const path = fairId ? `/imports/fair/${fairId}` : "/imports";
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };
  const goToFairDetail = (fairId: string) => {
    const path = `/fairs/${fairId}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const isCustomersActive = parsed.route === "/customers" || parsed.route === "/customers/:id";
  const isFairsActive = parsed.route === "/fairs" || parsed.route === "/fairs/:id";

  const breadcrumbs =
    parsed.route === "/customers/:id" && parsed.customerId
      ? [
          { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
          { label: labels.customers, onClick: goToCustomers },
          { label: customerName ?? uiLabels.navCustomers, current: true },
        ]
      : parsed.route === "/fairs/:id" && parsed.fairId
        ? [
            { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
            { label: uiLabels.navFairs, onClick: goToFairs },
            { label: fairName ?? uiLabels.navFairs, current: true },
          ]
        : parsed.route === "/fairs"
        ? [
            { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
            { label: uiLabels.navFairs, onClick: goToFairs },
            { label: uiLabels.navFairs, current: true },
          ]
        : parsed.route === "/imports"
          ? [
              { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
              { label: uiLabels.navImports, current: true },
            ]
          : [{ label: labels.customers, current: true }];

  const navItems = [
    {
      path: "/customers",
      label: uiLabels.navCustomers,
      active: isCustomersActive,
      onClick: (e: React.MouseEvent) => handleNav("/customers", e),
    },
    {
      path: "/fairs",
      label: uiLabels.navFairs,
      active: isFairsActive,
      onClick: (e: React.MouseEvent) => handleNav("/fairs", e),
    },
    {
      path: "/imports",
      label: uiLabels.navImports,
      active: parsed.route === "/imports" || parsed.route === "/imports/fair/:fairId",
      onClick: (e: React.MouseEvent) => handleNav("/imports", e),
    },
  ];

  return (
    <AppLayout
      breadcrumbs={breadcrumbs}
      navItems={navItems}
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen((v) => !v)}
    >
      {parsed.route === "/fairs" && <FairsPage onOpenDetail={goToFairDetail} />}
      {parsed.route === "/fairs/:id" && parsed.fairId && (
        <FairDetailPage
          fairId={parsed.fairId}
          onBack={goToFairs}
          onFairLoaded={setFairName}
          onOpenCustomer={goToCustomerDetail}
          onImportParticipants={() => goToImportWizard(parsed.fairId)}
        />
      )}
      {parsed.route === "/imports" && <ImportWizardPage />}
      {parsed.route === "/imports/fair/:fairId" && parsed.fairId && (
        <ImportWizardPage preselectedFairId={parsed.fairId} />
      )}
      {parsed.route === "/customers" && <CustomersPage onOpenDetail={goToCustomerDetail} />}
      {parsed.route === "/customers/:id" && parsed.customerId && (
        <CustomerDetailPage
          customerId={parsed.customerId}
          onBack={goToCustomers}
          onCustomerLoaded={setCustomerName}
        />
      )}
    </AppLayout>
  );
}

export default App;
