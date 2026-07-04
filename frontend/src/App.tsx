import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { FairDetailPage } from "./pages/FairDetailPage";
import { ImportWizardPage } from "./pages/ImportWizardPage";
import { DataIntegrationImportsPage } from "./pages/DataIntegrationImportsPage";
import { AdapterManagementPage } from "./pages/AdapterManagementPage";
import { DatabaseBackupsPage } from "./pages/DatabaseBackupsPage";
import { DataOperationsPage } from "./pages/DataOperationsPage";
import { DataOperationRunResultPage } from "./pages/DataOperationRunResultPage";
import { DataIntegrationLayout } from "./components/dataIntegration/DataIntegrationLayout";
import { AdminSystemLayout } from "./components/admin/AdminSystemLayout";
import { AppLayout } from "./components/layout/AppLayout";
import { Card } from "./components/ui/Card";
import { uiLabels } from "./labels/uiLabels";
import { dataIntegrationLabels } from "./labels/dataIntegrationLabels";
import { adminLabels } from "./labels/adminLabels";
import { labels } from "./labels";
import "./styles.css";

type AppRoute =
  | "/customers"
  | "/fairs"
  | "/fairs/:id"
  | "/data-integration/imports"
  | "/data-integration/imports/new"
  | "/data-integration/imports/fair/:fairId"
  | "/data-integration/imports/continue/:batchId"
  | "/data-integration/jobs"
  | "/data-integration/reports"
  | "/data-integration/adapters"
  | "/admin/system/backups"
  | "/admin/data-operations"
  | "/admin/data-operations/runs/:runId"
  | "/imports"
  | "/imports/fair/:fairId"
  | "/customers/:id";

interface ParsedRoute {
  route: AppRoute;
  customerId?: string;
  fairId?: string;
  batchId?: string;
  dataOperationRunId?: string;
  dataOperationKey?: string;
}

function parseRoute(location: string): ParsedRoute {
  const { pathname, search } = splitPath(location);
  const searchParams = new URLSearchParams(search);
  const dataOperationKey = searchParams.get("operation") ?? undefined;

  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    if (pathname === "/admin/data-operations" || pathname === "/admin/data-operations/") {
      return { route: "/admin/data-operations" };
    }
    const dataOpRun = pathname.match(/^\/admin\/data-operations\/runs\/([^/]+)$/);
    if (dataOpRun) {
      return {
        route: "/admin/data-operations/runs/:runId",
        dataOperationRunId: dataOpRun[1],
        dataOperationKey,
      };
    }
    if (pathname.startsWith("/admin/data-operations")) {
      return { route: "/admin/data-operations" };
    }
    if (pathname === "/admin/system/backups" || pathname.startsWith("/admin/system/backups")) {
      return { route: "/admin/system/backups" };
    }
    return { route: "/admin/system/backups" };
  }
  if (pathname === "/data-integration" || pathname.startsWith("/data-integration/")) {
    const continueImport = pathname.match(/^\/data-integration\/imports\/continue\/([^/]+)$/);
    if (continueImport) {
      return { route: "/data-integration/imports/continue/:batchId", batchId: continueImport[1] };
    }
    const fairImport = pathname.match(/^\/data-integration\/imports\/fair\/([^/]+)$/);
    if (fairImport) {
      return { route: "/data-integration/imports/fair/:fairId", fairId: fairImport[1] };
    }
    if (pathname === "/data-integration/imports/new") {
      return { route: "/data-integration/imports/new" };
    }
    if (pathname === "/data-integration/jobs") {
      return { route: "/data-integration/jobs" };
    }
    if (pathname === "/data-integration/reports") {
      return { route: "/data-integration/reports" };
    }
    if (pathname === "/data-integration/adapters") {
      return { route: "/data-integration/adapters" };
    }
    return { route: "/data-integration/imports" };
  }
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

function isDataIntegrationRoute(route: AppRoute): boolean {
  return route.startsWith("/data-integration");
}

function isAdminRoute(route: AppRoute): boolean {
  return route.startsWith("/admin");
}

function adminSection(route: AppRoute): string {
  if (route.includes("/data-operations/runs/")) return "data-operations";
  if (route.includes("/data-operations")) return "data-operations";
  if (route.includes("/backups")) return "backups";
  return "backups";
}

function diSection(route: AppRoute): string {
  if (route.includes("/adapters")) return "adapters";
  if (route.includes("/new") || route.includes("/fair/")) return "new";
  if (route.includes("/jobs")) return "jobs";
  if (route.includes("/reports")) return "reports";
  return "imports";
}

export function App() {
  const [parsed, setParsed] = React.useState<ParsedRoute>(() =>
    parseRoute(`${window.location.pathname}${window.location.search}`),
  );
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [customerName, setCustomerName] = React.useState<string | null>(null);
  const [fairName, setFairName] = React.useState<string | null>(null);
  const [diNotice, setDiNotice] = React.useState<string | null>(null);
  const [adminNotice, setAdminNotice] = React.useState<string | null>(null);

  React.useEffect(() => {
    const path = window.location.pathname;
    if (path === "/") {
      const next = `/customers${window.location.search}`;
      window.history.replaceState(null, "", next);
      setParsed(parseRoute("/customers"));
      return;
    }
    if (path === "/imports") {
      window.history.replaceState(null, "", "/data-integration/imports/new");
      setParsed(parseRoute("/data-integration/imports/new"));
      return;
    }
    const legacyFair = path.match(/^\/imports\/fair\/([^/]+)$/);
    if (legacyFair) {
      const next = `/data-integration/imports/fair/${legacyFair[1]}`;
      window.history.replaceState(null, "", next);
      setParsed(parseRoute(next));
    }
  }, []);

  React.useEffect(() => {
    const onPopState = () => {
      setParsed(parseRoute(`${window.location.pathname}${window.location.search}`));
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
    const { pathname } = splitPath(path);
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

  const goToDataIntegration = (subpath = "/data-integration/imports") => {
    navigate(subpath);
    setParsed(parseRoute(subpath));
    setSidebarOpen(false);
  };

  const goToImportWizard = (fairId?: string) => {
    const path = fairId
      ? `/data-integration/imports/fair/${fairId}`
      : "/data-integration/imports/new";
    goToDataIntegration(path);
  };

  const goToFairDetail = (fairId: string) => {
    const path = `/fairs/${fairId}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToAdmin = (subpath = "/admin/system/backups") => {
    navigate(subpath);
    setParsed(parseRoute(subpath));
    setSidebarOpen(false);
  };

  const isCustomersActive = parsed.route === "/customers" || parsed.route === "/customers/:id";
  const isFairsActive = parsed.route === "/fairs" || parsed.route === "/fairs/:id";
  const isDiActive = isDataIntegrationRoute(parsed.route);
  const isAdminActive = isAdminRoute(parsed.route);

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
          : isDiActive
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                { label: uiLabels.navImports, current: true },
              ]
            : isAdminActive
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                  { label: uiLabels.navAdmin, onClick: () => goToAdmin() },
                  {
                    label:
                      parsed.route === "/admin/data-operations/runs/:runId"
                        ? adminLabels.dataOpAnalyzeResultTitle
                        : parsed.route === "/admin/data-operations"
                          ? adminLabels.navDataOperations
                          : adminLabels.navDatabaseBackups,
                    current: true,
                  },
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
      path: "/data-integration/imports",
      label: uiLabels.navImports,
      active: isDiActive,
      onClick: (e: React.MouseEvent) => handleNav("/data-integration/imports", e),
    },
    {
      path: "/admin/system/backups",
      label: uiLabels.navAdmin,
      active: isAdminActive,
      onClick: (e: React.MouseEvent) => handleNav("/admin/system/backups", e),
    },
  ];

  const renderDataIntegration = () => (
    <DataIntegrationLayout
      activeSection={diSection(parsed.route)}
      onNavigate={(path, e) => handleNav(path, e)}
      onDisabledClick={() => setDiNotice(dataIntegrationLabels.comingSoonMessage)}
    >
      {diNotice && <p className="text-muted">{diNotice}</p>}
      {parsed.route === "/data-integration/imports" && (
        <DataIntegrationImportsPage
          onNewImport={() => goToDataIntegration("/data-integration/imports/new")}
          onContinueBatch={(batchId) => goToDataIntegration(`/data-integration/imports/continue/${batchId}`)}
        />
      )}
      {(parsed.route === "/data-integration/imports/new" ||
        parsed.route === "/data-integration/imports/fair/:fairId") && (
        <ImportWizardPage
          preselectedFairId={parsed.fairId}
          onUploadComplete={() => goToDataIntegration("/data-integration/imports")}
          onMappingSaved={() => goToDataIntegration("/data-integration/imports")}
        />
      )}
      {parsed.route === "/data-integration/imports/continue/:batchId" && (
        <ImportWizardPage
          resumeBatchId={parsed.batchId}
          onMappingSaved={() => goToDataIntegration("/data-integration/imports")}
          onFinished={() => goToDataIntegration("/data-integration/imports")}
        />
      )}
      {(parsed.route === "/data-integration/jobs" || parsed.route === "/data-integration/reports") && (
        <Card>
          <p>{dataIntegrationLabels.comingSoonMessage}</p>
        </Card>
      )}
      {parsed.route === "/data-integration/adapters" && (
        <AdapterManagementPage onOpenFair={goToFairDetail} />
      )}
    </DataIntegrationLayout>
  );

  const renderAdminSystem = () => (
    <AdminSystemLayout
      activeSection={adminSection(parsed.route)}
      onNavigate={(path, e) => handleNav(path, e)}
      onDisabledClick={() => setAdminNotice(adminLabels.comingSoonMessage)}
    >
      {adminNotice && <p className="text-muted">{adminNotice}</p>}
      {parsed.route === "/admin/system/backups" && <DatabaseBackupsPage />}
      {parsed.route === "/admin/data-operations" && (
        <DataOperationsPage
          onOpenResult={(runId, operationKey) =>
            goToAdmin(
              `/admin/data-operations/runs/${runId}?operation=${encodeURIComponent(operationKey)}`,
            )
          }
        />
      )}
      {parsed.route === "/admin/data-operations/runs/:runId" && parsed.dataOperationRunId && (
        <DataOperationRunResultPage
          runId={parsed.dataOperationRunId}
          operationKey={parsed.dataOperationKey}
          onBack={() => goToAdmin("/admin/data-operations")}
        />
      )}
    </AdminSystemLayout>
  );

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
      {isDiActive && renderDataIntegration()}
      {isAdminActive && renderAdminSystem()}
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
