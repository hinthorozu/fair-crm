import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { FairDetailPage } from "./pages/FairDetailPage";
import { ImportsPage } from "./pages/ImportsPage";
import { AppLayout } from "./components/layout/AppLayout";
import { uiLabels } from "./labels/uiLabels";
import { labels } from "./labels";
import "./styles.css";

type AppRoute = "/" | "/fairs" | "/fairs/:id" | "/imports" | "/customers/:id";

interface ParsedRoute {
  route: AppRoute;
  customerId?: string;
  fairId?: string;
}

function parseRoute(pathname: string): ParsedRoute {
  if (pathname === "/imports" || pathname.startsWith("/imports/")) {
    return { route: "/imports" };
  }
  if (pathname === "/fairs" || pathname.startsWith("/fairs/")) {
    const fairMatch = pathname.match(/^\/fairs\/([^/]+)$/);
    if (fairMatch) {
      return { route: "/fairs/:id", fairId: fairMatch[1] };
    }
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
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [customerName, setCustomerName] = React.useState<string | null>(null);
  const [fairName, setFairName] = React.useState<string | null>(null);

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
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
    if (path === "/") setCustomerName(null);
    if (path === "/fairs") setFairName(null);
  };

  const goToCustomerDetail = (customerId: string) => {
    const path = `/customers/${customerId}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToCustomers = () => {
    navigate("/");
    setParsed({ route: "/" });
    setCustomerName(null);
    setSidebarOpen(false);
  };

  const goToFairs = () => {
    navigate("/fairs");
    setParsed({ route: "/fairs" });
    setFairName(null);
    setSidebarOpen(false);
  };

  const goToFairDetail = (fairId: string) => {
    const path = `/fairs/${fairId}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const isCustomersActive = parsed.route === "/" || parsed.route === "/customers/:id";
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
      path: "/",
      label: uiLabels.navCustomers,
      active: isCustomersActive,
      onClick: (e: React.MouseEvent) => handleNav("/", e),
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
      active: parsed.route === "/imports",
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
        />
      )}
      {parsed.route === "/imports" && <ImportsPage />}
      {parsed.route === "/" && <CustomersPage onOpenDetail={goToCustomerDetail} />}
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
