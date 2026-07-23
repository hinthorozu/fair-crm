import React from "react";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { FairsPage } from "./pages/FairsPage";
import { FairDetailPage } from "./pages/FairDetailPage";
import { FairEnrichmentRunPage } from "./pages/FairEnrichmentRunPage";
import { ImportWizardPage } from "./pages/ImportWizardPage";
import { DataIntegrationImportsPage } from "./pages/DataIntegrationImportsPage";
import { AdapterManagementPage } from "./pages/AdapterManagementPage";
import { AdapterDetailPage } from "./pages/AdapterDetailPage";
import { ScraperRunHistoryPage } from "./pages/ScraperRunHistoryPage";
import { ScraperTestPage } from "./pages/ScraperTestPage";
import { EnrichmentRunDetailPage } from "./pages/EnrichmentRunDetailPage";
import { CustomerEnrichmentPage } from "./pages/CustomerEnrichmentPage";
import { DatabaseBackupsPage } from "./pages/DatabaseBackupsPage";
import { SmtpAccountsPage } from "./pages/SmtpAccountsPage";
import { MailTemplatesPage } from "./pages/MailTemplatesPage";
import { MailOperationsPage } from "./pages/MailOperationsPage";
import { DataOperationsPage } from "./pages/DataOperationsPage";
import { DataOperationRunResultPage } from "./pages/DataOperationRunResultPage";
import { OperationCapabilitiesAdminPage } from "./pages/OperationCapabilitiesAdminPage";
import { ActivitiesPage } from "./pages/ActivitiesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { TodoDetailPage } from "./pages/TodoDetailPage";
import { TodosPage } from "./pages/TodosPage";
import { OperationsPage } from "./pages/OperationsPage";
import { OperationDetailPage } from "./pages/OperationDetailPage";
import { ScraperOperationWizardPage } from "./pages/ScraperOperationWizardPage";
import { CustomersResponsivePilotPage } from "./dev/CustomersResponsivePilotPage";
import { TableStandardSmokePage } from "./dev/TableStandardSmokePage";
import { DataIntegrationLayout } from "./components/dataIntegration/DataIntegrationLayout";
import { AdminSystemLayout } from "./components/admin/AdminSystemLayout";
import { AppLayout } from "./components/layout/AppLayout";
import {
  NavIconActivities,
  NavIconAdmin,
  NavIconCustomers,
  NavIconDashboard,
  NavIconDataIntegration,
  NavIconFairs,
  NavIconOperations,
  NavIconTodos,
} from "./components/layout/NavIcons";
import { activityLabels } from "./labels/activityLabels";
import { operationLabels } from "./labels/operationLabels";
import type { OperationType } from "./types/operation";
import { EmptyState } from "./components/ui/EmptyState";
import {
  isNavigationDirty,
  useNavigationDirtyGate,
} from "./components/ui/form/FormDirty";
import { PageHeader } from "./components/ui/PageHeader";
import { PageShell } from "./components/ui/PageShell";
import { uiLabels } from "./labels/uiLabels";
import { dataIntegrationLabels } from "./labels/dataIntegrationLabels";
import { adminLabels } from "./labels/adminLabels";
import { labels } from "./labels";
import { scraperLabels } from "./labels/scraperLabels";
import { fairLabels } from "./labels/fairLabels";
import { dashboardLabels } from "./labels/dashboardLabels";
import { resolveRunDetailPath } from "./utils/enrichmentRunRouting";
import {
  CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
  isCustomerContactEnrichmentAdapter,
} from "./utils/enrichmentAdapter";
import { useDocumentTitle } from "./hooks/useDocumentTitle";
import { useAuth } from "./auth/AuthContext";
import { config } from "./config";
import "./styles.css";

type AppRoute =
  | "/login"
  | "/dashboard"
  | "/customers"
  | "/fairs"
  | "/fairs/:id"
  | "/fairs/:id/enrichment"
  | "/todos"
  | "/todos/:id"
  | "/operations"
  | "/operations/new/scraper"
  | "/operations/:id"
  | "/follow-ups"
  | "/activities"
  | "/data-integration/imports"
  | "/data-integration/imports/new"
  | "/data-integration/imports/fair/:fairId"
  | "/data-integration/imports/continue/:batchId"
  | "/data-integration/jobs"
  | "/data-integration/reports"
  | "/data-integration/adapters"
  | "/data-integration/adapters/:adapterKey"
  | "/data-integration/run-history"
  | "/data-integration/runs/:runId"
  | "/data-integration/scraper-test"
  | "/data-integration/enrichment"
  | "/admin/system/backups"
  | "/admin/smtp-operations/accounts"
  | "/admin/smtp-operations/templates"
  | "/admin/smtp-operations/mail-operations"
  | "/admin/data-operations"
  | "/admin/data-operations/runs/:runId"
  | "/admin/operation-capabilities"
  | "/imports"
  | "/imports/fair/:fairId"
  | "/customers/:id";

interface ParsedRoute {
  route: AppRoute;
  customerId?: string;
  fairId?: string;
  todoId?: string;
  operationId?: string;
  batchId?: string;
  dataOperationRunId?: string;
  dataOperationKey?: string;
  adapterKey?: string;
  runId?: string;
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
    if (
      pathname === "/admin/operation-capabilities" ||
      pathname.startsWith("/admin/operation-capabilities/")
    ) {
      return { route: "/admin/operation-capabilities" };
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
    const runDetail = pathname.match(/^\/data-integration\/runs\/([^/]+)$/);
    if (runDetail) {
      return {
        route: "/data-integration/runs/:runId",
        runId: decodeURIComponent(runDetail[1]),
        adapterKey: searchParams.get("adapter_key") ?? undefined,
      };
    }
    if (pathname === "/data-integration/scraper-test" || pathname === "/data-integration/scraper-test/") {
      return { route: "/data-integration/scraper-test" };
    }
    if (pathname === "/data-integration/enrichment" || pathname === "/data-integration/enrichment/") {
      return { route: "/data-integration/enrichment" };
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
    const fairEnrichment = pathname.match(/^\/fairs\/([^/]+)\/enrichment$/);
    if (fairEnrichment) {
      return { route: "/fairs/:id/enrichment", fairId: fairEnrichment[1] };
    }
    const fairMatch = pathname.match(/^\/fairs\/([^/]+)$/);
    if (fairMatch) {
      return { route: "/fairs/:id", fairId: fairMatch[1] };
    }
    return { route: "/fairs" };
  }
  if (pathname === "/follow-ups" || pathname.startsWith("/follow-ups/")) {
    return { route: "/follow-ups" };
  }
  if (pathname === "/activities" || pathname.startsWith("/activities/")) {
    return { route: "/activities" };
  }
  if (pathname === "/todos" || pathname.startsWith("/todos/")) {
    const todoMatch = pathname.match(/^\/todos\/([^/]+)$/);
    if (todoMatch) {
      return { route: "/todos/:id", todoId: todoMatch[1] };
    }
    return { route: "/todos" };
  }
  if (pathname === "/operations" || pathname.startsWith("/operations/")) {
    if (pathname === "/operations/new/scraper" || pathname === "/operations/new/scraper/") {
      return { route: "/operations/new/scraper" };
    }
    // Legacy: type picker is a modal on /operations (not a standalone page).
    if (
      pathname === "/operations/new" ||
      pathname === "/operations/new/" ||
      pathname === "/operations/new/manual_task" ||
      pathname === "/operations/new/manual_task/"
    ) {
      return { route: "/operations" };
    }
    const operationMatch = pathname.match(/^\/operations\/([^/]+)$/);
    if (operationMatch) {
      return { route: "/operations/:id", operationId: operationMatch[1] };
    }
    return { route: "/operations" };
  }
  if (pathname === "/login" || pathname === "/login/") {
    return { route: "/login" };
  }
  if (pathname === "/dashboard" || pathname === "/") {
    return { route: "/dashboard" };
  }
  if (pathname === "/customers") {
    return { route: "/customers" };
  }
  const customerMatch = pathname.match(/^\/customers\/([^/]+)$/);
  if (customerMatch) {
    return { route: "/customers/:id", customerId: customerMatch[1] };
  }
  return { route: "/dashboard" };
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
  if (route.includes("/operation-capabilities")) return "operation-capabilities";
  if (route.includes("/smtp-operations/templates")) return "mail-templates";
  if (route.includes("/smtp-operations/mail-operations")) return "mail-operations";
  if (route.includes("/smtp-operations/accounts")) return "smtp";
  if (route.includes("/backups")) return "backups";
  return "backups";
}

function diSection(route: AppRoute): string {
  if (route.includes("/scraper-test")) return "scraper-test";
  if (route.includes("/enrichment") || route.includes("/runs/")) return "enrichment";
  if (route.includes("/run-history")) return "run-history";
  if (route.includes("/adapters")) return "adapters";
  if (route.includes("/new") || route.includes("/fair/")) return "new";
  if (route.includes("/jobs")) return "jobs";
  if (route.includes("/reports")) return "reports";
  return "imports";
}

export function App() {
  const { isAuthenticated, logout } = useAuth();
  const [parsed, setParsed] = React.useState<ParsedRoute>(() =>
    parseRoute(`${window.location.pathname}${window.location.search}`),
  );
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [customerName, setCustomerName] = React.useState<string | null>(null);
  const [fairName, setFairName] = React.useState<string | null>(null);
  const [todoTitle, setTodoTitle] = React.useState<string | null>(null);
  const [adapterName, setAdapterName] = React.useState<string | null>(null);
  const [diNotice, setDiNotice] = React.useState<string | null>(null);
  const [adminNotice, setAdminNotice] = React.useState<string | null>(null);
  const { requestNavigation, confirmDialog } = useNavigationDirtyGate();
  const allowedUrlRef = React.useRef(
    `${window.location.pathname}${window.location.search}`,
  );

  const runGuardedNav = React.useCallback(
    (action: () => void) => {
      requestNavigation(() => {
        action();
        allowedUrlRef.current = `${window.location.pathname}${window.location.search}`;
      });
    },
    [requestNavigation],
  );

  useDocumentTitle({
    route: parsed.route,
    customerName,
    fairName,
    todoTitle,
    adapterName,
    adapterKey: parsed.adapterKey,
    dataOperationKey: parsed.dataOperationKey,
  });

  React.useLayoutEffect(() => {
    const path = window.location.pathname;
    if (import.meta.env.DEV && path === "/dev/customers-responsive-pilot") {
      return;
    }
    if (import.meta.env.DEV && path === "/dev/table-standard-smoke") {
      return;
    }
    if (!isAuthenticated && path !== "/login") {
      window.history.replaceState(null, "", "/login");
      setParsed({ route: "/login" });
      return;
    }
    if (isAuthenticated && path === "/login") {
      window.history.replaceState(null, "", "/dashboard");
      setParsed({ route: "/dashboard" });
    }
  }, [isAuthenticated]);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    const path = window.location.pathname;
    if (path === "/") {
      const next = `/dashboard${window.location.search}`;
      window.history.replaceState(null, "", next);
      setParsed(parseRoute("/dashboard"));
      return;
    }
    if (path === "/imports") {
      window.history.replaceState(null, "", "/data-integration/imports/new");
      setParsed(parseRoute("/data-integration/imports/new"));
      return;
    }
    if (path === "/follow-ups" || path.startsWith("/follow-ups/")) {
      window.history.replaceState(null, "", "/todos?view=follow_ups");
      setParsed(parseRoute("/todos?view=follow_ups"));
      return;
    }
    if (
      path === "/operations/new" ||
      path === "/operations/new/" ||
      path === "/operations/new/manual_task" ||
      path === "/operations/new/manual_task/"
    ) {
      window.history.replaceState(null, "", "/operations");
      setParsed({ route: "/operations" });
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
      const next = `${window.location.pathname}${window.location.search}`;
      if (isNavigationDirty()) {
        window.history.pushState(null, "", allowedUrlRef.current);
        requestNavigation(() => {
          window.history.pushState(null, "", next);
          allowedUrlRef.current = next;
          setParsed(parseRoute(next));
          setSidebarOpen(false);
        });
        return;
      }
      allowedUrlRef.current = next;
      setParsed(parseRoute(next));
      setSidebarOpen(false);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [requestNavigation]);

  const handleNav = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
      const { pathname } = splitPath(path);
      if (pathname === "/customers") setCustomerName(null);
      if (pathname === "/fairs") setFairName(null);
      if (!pathname.match(/^\/data-integration\/adapters\/[^/]+$/)) setAdapterName(null);
    });
  };

  const goToCustomerDetail = (customerId: string) => {
    const path = `/customers/${customerId}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToDashboard = () => {
    runGuardedNav(() => {
      navigate("/dashboard");
      setParsed({ route: "/dashboard" });
      setSidebarOpen(false);
    });
  };

  const goToCustomers = () => {
    runGuardedNav(() => {
      navigate("/customers");
      setParsed({ route: "/customers" });
      setCustomerName(null);
      setSidebarOpen(false);
    });
  };

  const goToFairs = () => {
    runGuardedNav(() => {
      navigate("/fairs");
      setParsed({ route: "/fairs" });
      setFairName(null);
      setSidebarOpen(false);
    });
  };

  const goToDataIntegration = (subpath = "/data-integration/imports") => {
    runGuardedNav(() => {
      navigate(subpath);
      setParsed(parseRoute(subpath));
      setSidebarOpen(false);
    });
  };

  const goToImportWizard = (fairId?: string) => {
    const path = fairId
      ? `/data-integration/imports/fair/${fairId}`
      : "/data-integration/imports/new";
    goToDataIntegration(path);
  };

  const goToFairDetail = (fairId: string) => {
    const path = `/fairs/${fairId}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToFairEnrichment = (fairId: string) => {
    const path = `/fairs/${fairId}/enrichment`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToTodos = () => {
    runGuardedNav(() => {
      navigate("/todos");
      setParsed({ route: "/todos" });
      setTodoTitle(null);
      setSidebarOpen(false);
    });
  };

  const goToActivities = () => {
    runGuardedNav(() => {
      navigate("/activities");
      setParsed({ route: "/activities" });
      setSidebarOpen(false);
    });
  };

  const goToTodoDetail = (todoId: string) => {
    const path = `/todos/${todoId}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToOperations = () => {
    runGuardedNav(() => {
      navigate("/operations");
      setParsed({ route: "/operations" });
      setSidebarOpen(false);
    });
  };

  const goToOperationDetail = (operationId: string) => {
    const path = `/operations/${operationId}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToOperationTypeWizard = (type: OperationType) => {
    if (type === "scraper") {
      runGuardedNav(() => {
        navigate("/operations/new/scraper");
        setParsed({ route: "/operations/new/scraper" });
        setSidebarOpen(false);
      });
    }
  };

  const goToAdapters = () => {
    runGuardedNav(() => {
      navigate("/data-integration/adapters");
      setParsed({ route: "/data-integration/adapters" });
      setAdapterName(null);
      setSidebarOpen(false);
    });
  };

  const goToAdapterDetail = (adapterKey: string) => {
    const path = `/data-integration/adapters/${encodeURIComponent(adapterKey)}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToRunHistory = (adapterKey?: string) => {
    const path = adapterKey
      ? `/data-integration/run-history?adapter_key=${encodeURIComponent(adapterKey)}`
      : "/data-integration/run-history";
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToScraperTest = (adapterKey?: string, runId?: string) => {
    const params = new URLSearchParams();
    if (adapterKey) params.set("adapter_key", adapterKey);
    if (runId) params.set("run", runId);
    const qs = params.toString();
    const path = `/data-integration/scraper-test${qs ? `?${qs}` : ""}`;
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToAdapterRunDetail = (adapterKey: string, runId: string) => {
    const path = resolveRunDetailPath(adapterKey, runId);
    runGuardedNav(() => {
      navigate(path);
      setParsed(parseRoute(path));
      setSidebarOpen(false);
    });
  };

  const goToAdmin = (subpath = "/admin/system/backups") => {
    runGuardedNav(() => {
      navigate(subpath);
      setParsed(parseRoute(subpath));
      setSidebarOpen(false);
    });
  };

  const handleLoginSuccess = React.useCallback(() => {
    window.history.replaceState(null, "", "/dashboard");
    setParsed({ route: "/dashboard" });
    setSidebarOpen(false);
    allowedUrlRef.current = "/dashboard";
  }, []);

  const handleLogout = React.useCallback(async () => {
    const finishLogout = async () => {
      await logout();
      // VITE_DEV_BYPASS_ENABLED keeps the app usable without a Core session.
      if (config.devBypassEnabled) {
        setSidebarOpen(false);
        return;
      }
      window.history.replaceState(null, "", "/login");
      setParsed({ route: "/login" });
      setSidebarOpen(false);
      allowedUrlRef.current = "/login";
    };
    requestNavigation(() => {
      void finishLogout();
    });
  }, [logout, requestNavigation]);

  const isDashboardActive = parsed.route === "/dashboard";
  const isCustomersActive = parsed.route === "/customers" || parsed.route === "/customers/:id";
  const isFairsActive =
    parsed.route === "/fairs" ||
    parsed.route === "/fairs/:id" ||
    parsed.route === "/fairs/:id/enrichment";
  const isTodosActive =
    parsed.route === "/todos" || parsed.route === "/todos/:id";
  const isOperationsActive =
    parsed.route === "/operations" ||
    parsed.route === "/operations/new/scraper" ||
    parsed.route === "/operations/:id";
  const isActivitiesActive = parsed.route === "/activities";
  const isDiActive = isDataIntegrationRoute(parsed.route);
  const isAdminActive = isAdminRoute(parsed.route);

  const breadcrumbs =
    parsed.route === "/dashboard"
      ? [{ label: dashboardLabels.pageTitle, current: true }]
      : parsed.route === "/customers/:id" && parsed.customerId
      ? [
          { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
          { label: labels.customers, onClick: goToCustomers },
          { label: customerName ?? uiLabels.navCustomers, current: true },
        ]
      : parsed.route === "/fairs/:id/enrichment" && parsed.fairId
        ? [
            { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
            { label: uiLabels.navFairs, onClick: goToFairs },
            { label: fairName ?? uiLabels.navFairs, onClick: () => goToFairDetail(parsed.fairId!) },
            { label: fairLabels.enrichFairAction, current: true },
          ]
      : parsed.route === "/fairs/:id" && parsed.fairId
        ? [
            { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
            { label: uiLabels.navFairs, onClick: goToFairs },
            { label: fairName ?? uiLabels.navFairs, current: true },
          ]
        : parsed.route === "/fairs"
          ? [
              { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
              { label: uiLabels.navFairs, onClick: goToFairs },
              { label: uiLabels.navFairs, current: true },
            ]
          : parsed.route === "/todos/:id" && parsed.todoId
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navTodos, onClick: goToTodos },
                { label: todoTitle ?? uiLabels.navTodos, current: true },
              ]
          : parsed.route === "/todos"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navTodos, current: true },
              ]
          : parsed.route === "/operations/:id"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navOperations, onClick: goToOperations },
                { label: operationLabels.detailTitle, current: true },
              ]
          : parsed.route === "/operations/new/scraper"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navOperations, onClick: goToOperations },
                { label: operationLabels.scraperWizardTitle, current: true },
              ]
          : parsed.route === "/operations"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navOperations, current: true },
              ]
          : parsed.route === "/activities"
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: activityLabels.pageTitle, current: true },
              ]
          : parsed.route === "/data-integration/adapters/:adapterKey" && parsed.adapterKey
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                { label: scraperLabels.pageTitle, onClick: goToAdapters },
                { label: adapterName ?? parsed.adapterKey, current: true },
              ]
            : parsed.route === "/data-integration/adapters"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.pageTitle, current: true },
                ]
              : parsed.route === "/data-integration/runs/:runId"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  {
                    label: dataIntegrationLabels.navEnrichment,
                    onClick: () => goToDataIntegration("/data-integration/enrichment"),
                  },
                  { label: scraperLabels.enrichmentRunDetailTitle, current: true },
                ]
            : parsed.route === "/data-integration/enrichment"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: dataIntegrationLabels.navEnrichment, current: true },
                ]
            : parsed.route === "/data-integration/scraper-test"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.testPageTitle, current: true },
                ]
            : parsed.route === "/data-integration/run-history"
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                  { label: uiLabels.navImports, onClick: () => goToDataIntegration() },
                  { label: scraperLabels.runHistoryTitle, current: true },
                ]
            : isDiActive
            ? [
                { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                { label: uiLabels.navImports, current: true },
              ]
            : isAdminActive
              ? [
                  { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
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
                          : parsed.route === "/admin/operation-capabilities"
                            ? adminLabels.navOperationCapabilities
                          : adminLabels.navDatabaseBackups,
                    current: true,
                  },
                ]
              : parsed.route === "/customers"
                ? [
                    { label: uiLabels.breadcrumbHome, onClick: goToDashboard },
                    { label: labels.customers, current: true },
                  ]
              : [{ label: dashboardLabels.pageTitle, current: true }];

  const navItems = [
    {
      path: "/dashboard",
      label: uiLabels.navDashboard,
      icon: <NavIconDashboard />,
      active: isDashboardActive,
      onClick: (e: React.MouseEvent) => handleNav("/dashboard", e),
    },
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
      path: "/operations",
      label: uiLabels.navOperations,
      icon: <NavIconOperations />,
      active: isOperationsActive,
      onClick: (e: React.MouseEvent) => handleNav("/operations", e),
    },
    {
      path: "/activities",
      label: uiLabels.navActivities,
      icon: <NavIconActivities />,
      active: isActivitiesActive,
      onClick: (e: React.MouseEvent) => handleNav("/activities", e),
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
          onFinished={() => goToDataIntegration("/data-integration/imports")}
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
        <PageShell>
          <PageHeader
            title={
              parsed.route === "/data-integration/jobs"
                ? dataIntegrationLabels.navJobs
                : dataIntegrationLabels.navReports
            }
          />
          <EmptyState
            title={dataIntegrationLabels.comingSoon}
            description={dataIntegrationLabels.comingSoonMessage}
          />
        </PageShell>
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
      {parsed.route === "/data-integration/runs/:runId" && parsed.runId && (
        <EnrichmentRunDetailPage
          runId={parsed.runId}
          adapterKey={parsed.adapterKey}
          onBack={() => {
            if (parsed.adapterKey && isCustomerContactEnrichmentAdapter(parsed.adapterKey)) {
              goToDataIntegration("/data-integration/enrichment");
              return;
            }
            goToRunHistory(parsed.adapterKey);
          }}
          onOpenImportBatch={(batchId) =>
            goToDataIntegration(`/data-integration/imports/continue/${batchId}`)
          }
        />
      )}
      {parsed.route === "/data-integration/enrichment" && (
        <CustomerEnrichmentPage
          onRunStarted={(runId) =>
            goToAdapterRunDetail(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY, runId)
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
      {parsed.route === "/admin/operation-capabilities" && <OperationCapabilitiesAdminPage />}
    </AdminSystemLayout>
  );

  if (import.meta.env.DEV && window.location.pathname === "/dev/customers-responsive-pilot") {
    return <CustomersResponsivePilotPage />;
  }

  if (import.meta.env.DEV && window.location.pathname === "/dev/table-standard-smoke") {
    return <TableStandardSmokePage />;
  }

  if (!isAuthenticated) {
    return <LoginPage onSuccess={handleLoginSuccess} />;
  }

  return (
    <AppLayout
      breadcrumbs={breadcrumbs}
      navItems={navItems}
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen((v) => !v)}
      onLogout={handleLogout}
    >
      {parsed.route === "/dashboard" && (
        <DashboardPage
          onOpenCustomer={goToCustomerDetail}
          onNavigate={(path) => {
            runGuardedNav(() => {
              navigate(path);
              setParsed(parseRoute(path));
              setSidebarOpen(false);
            });
          }}
        />
      )}
      {parsed.route === "/fairs" && <FairsPage onOpenDetail={goToFairDetail} />}
      {parsed.route === "/fairs/:id" && parsed.fairId && (
        <FairDetailPage
          fairId={parsed.fairId}
          onBack={goToFairs}
          onFairLoaded={setFairName}
          onOpenCustomer={goToCustomerDetail}
          onImportParticipants={() => goToImportWizard(parsed.fairId)}
          onOpenFairEnrichment={goToFairEnrichment}
        />
      )}
      {parsed.route === "/fairs/:id/enrichment" && parsed.fairId && (
        <FairEnrichmentRunPage
          fairId={parsed.fairId}
          onBack={() => goToFairDetail(parsed.fairId!)}
          onFairLoaded={setFairName}
          onRunStarted={(runId) =>
            goToAdapterRunDetail(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY, runId)
          }
        />
      )}
      {isDiActive && renderDataIntegration()}
      {isAdminActive && renderAdminSystem()}
      {parsed.route === "/todos" && (
        <TodosPage onOpenDetail={goToTodoDetail} onOpenCustomer={goToCustomerDetail} />
      )}
      {parsed.route === "/todos/:id" && parsed.todoId && (
        <TodoDetailPage
          todoId={parsed.todoId}
          onBack={goToTodos}
          onTodoLoaded={setTodoTitle}
          onOpenCustomer={goToCustomerDetail}
        />
      )}
      {parsed.route === "/operations" && (
        <OperationsPage
          onOpenDetail={goToOperationDetail}
          onSelectType={goToOperationTypeWizard}
        />
      )}
      {parsed.route === "/operations/new/scraper" && (
        <ScraperOperationWizardPage
          onCancel={goToOperations}
          onCreated={goToOperationDetail}
        />
      )}
      {parsed.route === "/operations/:id" && parsed.operationId && (
        <OperationDetailPage
          operationId={parsed.operationId}
          onBack={goToOperations}
          onOpenTodo={goToTodoDetail}
          onOpenImportBatch={(batchId) =>
            goToDataIntegration(`/data-integration/imports/continue/${batchId}`)
          }
        />
      )}
      {parsed.route === "/activities" && (
        <ActivitiesPage onOpenCustomer={goToCustomerDetail} />
      )}
      {parsed.route === "/customers" && <CustomersPage onOpenDetail={goToCustomerDetail} />}
      {parsed.route === "/customers/:id" && parsed.customerId && (
        <CustomerDetailPage
          customerId={parsed.customerId}
          onBack={goToCustomers}
          onCustomerLoaded={setCustomerName}
          onOpenImportBatch={(batchId) =>
            goToDataIntegration(`/data-integration/imports/continue/${batchId}`)
          }
        />
      )}
      {confirmDialog}
    </AppLayout>
  );
}

export default App;
