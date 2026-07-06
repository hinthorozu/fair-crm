import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { FairDetailPage } from "./pages/FairDetailPage";
import { ImportWizardPage } from "./pages/ImportWizardPage";
import { DataIntegrationImportsPage } from "./pages/DataIntegrationImportsPage";
import { AdapterManagementPage } from "./pages/AdapterManagementPage";
import { AdapterDetailPage } from "./pages/AdapterDetailPage";
import { ScraperRunHistoryPage } from "./pages/ScraperRunHistoryPage";
import { ScraperTestPage } from "./pages/ScraperTestPage";
import { DatabaseBackupsPage } from "./pages/DatabaseBackupsPage";
import { SmtpAccountsPage } from "./pages/SmtpAccountsPage";
import { MailTemplatesPage } from "./pages/MailTemplatesPage";
import { MailOperationsPage } from "./pages/MailOperationsPage";
import { DataOperationsPage } from "./pages/DataOperationsPage";
import { DataOperationRunResultPage } from "./pages/DataOperationRunResultPage";
import { TodosPage } from "./pages/TodosPage";
import { DataIntegrationLayout } from "./components/dataIntegration/DataIntegrationLayout";
import { AdminSystemLayout } from "./components/admin/AdminSystemLayout";
import { AppLayout } from "./components/layout/AppLayout";
import {
  NavIconAdmin,
  NavIconCustomers,
  NavIconDataIntegration,
  NavIconFairs,
  NavIconTodos,
} from "./components/layout/NavIcons";
import { Card } from "./components/ui/Card";
import { uiLabels } from "./labels/uiLabels";
import { dataIntegrationLabels } from "./labels/dataIntegrationLabels";
import { adminLabels } from "./labels/adminLabels";
import { labels } from "./labels";
import { scraperLabels } from "./labels/scraperLabels";
import { useDocumentTitle } from "./hooks/useDocumentTitle";
import "./styles.css";

type AppRoute =
  | "/customers"
  | "/fairs"
  | "/fairs/:id"
  | "/todos"
  | "/data-integration/imports"
  | "/data-integration/imports/new"
  | "/data-integration/imports/fair/:fairId"
  | "/data-integration/imports/continue/:batchId"
  | "/data-integration/jobs"
  | "/data-integration/reports"
  | "/data-integration/adapters"
  | "/data-integration/adapters/:adapterKey"
  | "/data-integration/run-history"
  | "/data-integration/scraper-test"
  | "/admin/system/backups"
  | "/admin/smtp-operations/accounts"
  | "/admin/smtp-operations/templates"
  | "/admin/smtp-operations/mail-operations"
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
  adapterKey?: string;
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
    if (
      pathname === "/admin/smtp-operations/accounts" ||
      pathname.startsWith("/admin/smtp-operations/accounts/")
    ) {
      return { route: "/admin/smtp-operations/accounts" };
    }
    if (
      pathname === "/admin/smtp-operations/templates" ||
      pathname.startsWith("/admin/smtp-operations/templates/")
    ) {
      return { route: "/admin/smtp-operations/templates" };
    }
    if (
      pathname === "/admin/smtp-operations/mail-operations" ||
      pathname.startsWith("/admin/smtp-operations/mail-operations/")
    ) {
      return { route: "/admin/smtp-operations/mail-operations" };
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
    if (pathname === "/data-integration/run-history" || pathname === "/data-integration/run-history/") {
      return { route: "/data-integration/run-history" };
    }
    if (pathname === "/data-integration/scraper-test" || pathname === "/data-integration/scraper-test/") {
      return { route: "/data-integration/scraper-test" };
    }
    const adapterDetail = pathname.match(/^\/data-integration\/adapters\/([^/]+)$/);
    if (adapterDetail) {
      return {
        route: "/data-integration/adapters/:adapterKey",
        adapterKey: decodeURIComponent(adapterDetail[1]),
      };
    }
    if (pathname === "/data-integration/adapters" || pathname === "/data-integration/adapters/") {
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
  if (pathname === "/todos" || pathname === "/todos/") {
    return { route: "/todos" };
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
  if (route.includes("/smtp-operations/templates")) return "mail-templates";
  if (route.includes("/smtp-operations/mail-operations")) return "mail-operations";
  if (route.includes("/smtp-operations/accounts")) return "smtp";
  if (route.includes("/backups")) return "backups";
  return "backups";
}

function diSection(route: AppRoute): string {
  if (route.includes("/scraper-test")) return "scraper-test";
  if (route.includes("/run-history")) return "run-history";
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
  const [adapterName, setAdapterName] = React.useState<string | null>(null);
  const [diNotice, setDiNotice] = React.useState<string | null>(null);
  const [adminNotice, setAdminNotice] = React.useState<string | null>(null);

  useDocumentTitle({
    route: parsed.route,
    customerName,
    fairName,
    adapterName,
    adapterKey: parsed.adapterKey,
    dataOperationKey: parsed.dataOperationKey,
  });

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
    if (path === "/data-integration/adapters" || path === "/data-integration/adapters/") {
      const legacyAdapter = new URLSearchParams(window.location.search).get("adapter");
      if (legacyAdapter) {
        const next = `/data-integration/adapters/${encodeURIComponent(legacyAdapter)}`;
        window.history.replaceState(null, "", next);
        setParsed(parseRoute(next));
      }
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
    if (!pathname.match(/^\/data-integration\/adapters\/[^/]+$/)) setAdapterName(null);
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

  const goToAdapters = () => {
    navigate("/data-integration/adapters");
    setParsed({ route: "/data-integration/adapters" });
    setAdapterName(null);
    setSidebarOpen(false);
  };

  const goToAdapterDetail = (adapterKey: string) => {
    const path = `/data-integration/adapters/${encodeURIComponent(adapterKey)}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToRunHistory = (adapterKey?: string) => {
    const path = adapterKey
      ? `/data-integration/run-history?adapter_key=${encodeURIComponent(adapterKey)}`
      : "/data-integration/run-history";
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToScraperTest = (adapterKey?: string, runId?: string) => {
    const params = new URLSearchParams();
    if (adapterKey) params.set("adapter_key", adapterKey);
    if (runId) params.set("run", runId);
    const qs = params.toString();
    const path = `/data-integration/scraper-test${qs ? `?${qs}` : ""}`;
    navigate(path);
    setParsed(parseRoute(path));
    setSidebarOpen(false);
  };

  const goToAdapterRunDetail = (adapterKey: string, runId: string) => {
    goToScraperTest(adapterKey, runId);
  };

  const goToAdmin = (subpath = "/admin/system/backups") => {
    navigate(subpath);
    setParsed(parseRoute(subpath));
    setSidebarOpen(false);
  };

  const isCustomersActive = parsed.route === "/customers" || parsed.route === "/customers/:id";
  const isFairsActive = parsed.route === "/fairs" || parsed.route === "/fairs/:id";
  const isTodosActive = parsed.route === "/todos";
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
          : parsed.route === "/todos"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                { label: uiLabels.navTodos, current: true },
              ]
          : parsed.route === "/data-integration/adapters/:adapterKey" && parsed.adapterKey
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                { label: scraperLabels.pageTitle, onClick: goToAdapters },
                { label: adapterName ?? parsed.adapterKey, current: true },
              ]
            : parsed.route === "/data-integration/adapters"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.pageTitle, current: true },
                ]
              : parsed.route === "/data-integration/scraper-test"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.testPageTitle, current: true },
                ]
            : parsed.route === "/data-integration/run-history"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToCustomers },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.runHistoryTitle, current: true },
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
                        : parsed.route === "/admin/smtp-operations/accounts"
                          ? adminLabels.navSmtpAccounts
                          : parsed.route === "/admin/smtp-operations/templates"
                            ? adminLabels.navMailTemplates
                            : parsed.route === "/admin/smtp-operations/mail-operations"
                              ? adminLabels.navMailOperations
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
      icon: <NavIconCustomers />,
      active: isCustomersActive,
      onClick: (e: React.MouseEvent) => handleNav("/customers", e),
    },
    {
      path: "/fairs",
      label: uiLabels.navFairs,
      icon: <NavIconFairs />,
      active: isFairsActive,
      onClick: (e: React.MouseEvent) => handleNav("/fairs", e),
    },
    {
      path: "/todos",
      label: uiLabels.navTodos,
      icon: <NavIconTodos />,
      active: isTodosActive,
      onClick: (e: React.MouseEvent) => handleNav("/todos", e),
    },
    {
      path: "/data-integration/imports",
      label: uiLabels.navImports,
      icon: <NavIconDataIntegration />,
      active: isDiActive,
      onClick: (e: React.MouseEvent) => handleNav("/data-integration/imports", e),
    },
    {
      path: "/admin/system/backups",
      label: uiLabels.navAdmin,
      icon: <NavIconAdmin />,
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
        <AdapterManagementPage onOpenDetail={goToAdapterDetail} />
      )}
      {parsed.route === "/data-integration/adapters/:adapterKey" && parsed.adapterKey && (
        <AdapterDetailPage
          adapterKey={parsed.adapterKey}
          onBack={goToAdapters}
          onOpenFair={goToFairDetail}
          onAdapterLoaded={setAdapterName}
          onViewAllRuns={goToRunHistory}
          onOpenScraperTest={goToScraperTest}
          onOpenRunDetail={goToAdapterRunDetail}
        />
      )}
      {parsed.route === "/data-integration/run-history" && (
        <ScraperRunHistoryPage
          initialAdapterKey={new URLSearchParams(window.location.search).get("adapter_key") ?? undefined}
          onOpenAdapter={goToAdapterDetail}
          onOpenRunDetail={goToAdapterRunDetail}
          onOpenImportBatch={(batchId) =>
            goToDataIntegration(`/data-integration/imports/continue/${batchId}`)
          }
        />
      )}
      {parsed.route === "/data-integration/scraper-test" && (
        <ScraperTestPage
          initialAdapterKey={new URLSearchParams(window.location.search).get("adapter_key") ?? undefined}
          focusRunId={new URLSearchParams(window.location.search).get("run")}
        />
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
      {parsed.route === "/admin/smtp-operations/accounts" && <SmtpAccountsPage />}
      {parsed.route === "/admin/smtp-operations/templates" && <MailTemplatesPage />}
      {parsed.route === "/admin/smtp-operations/mail-operations" && <MailOperationsPage />}
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
          onOpenImportDecisions={(batchId) =>
            goToDataIntegration(`/data-integration/imports/continue/${batchId}`)
          }
        />
      )}
      {isDiActive && renderDataIntegration()}
      {isAdminActive && renderAdminSystem()}
      {parsed.route === "/todos" && <TodosPage />}
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
