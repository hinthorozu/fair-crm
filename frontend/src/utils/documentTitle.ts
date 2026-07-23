import { labels } from "../labels";
import { adminLabels } from "../labels/adminLabels";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { fairLabels } from "../labels/fairLabels";
import { importLabels } from "../labels/importLabels";
import { scraperLabels } from "../labels/scraperLabels";
import { followUpLabels } from "../labels/followUpLabels";
import { dashboardLabels } from "../labels/dashboardLabels";
import { authLabels } from "../labels/authLabels";
import { todoLabels } from "../labels/todoLabels";
import { activityLabels } from "../labels/activityLabels";
import { operationLabels } from "../labels/operationLabels";
import { uiLabels } from "../labels/uiLabels";

export const DOCUMENT_TITLE_BRAND = labels.appTitle;

export const DUPLICATE_OPERATION_KEY = "duplicate_customer_analysis";

export interface DocumentTitleContext {
  route: string;
  pathname?: string;
  search?: string;
  customerName?: string | null;
  fairName?: string | null;
  todoTitle?: string | null;
  adapterName?: string | null;
  adapterKey?: string | null;
  dataOperationKey?: string | null;
}

export function formatDocumentTitle(pageTitle: string | null | undefined): string {
  const trimmed = pageTitle?.trim();
  return trimmed ? `${DOCUMENT_TITLE_BRAND} — ${trimmed}` : DOCUMENT_TITLE_BRAND;
}

function isDuplicateDataOperationRoute(
  operationKey: string | null,
  groupKey: string | null,
): boolean {
  if (operationKey === DUPLICATE_OPERATION_KEY) {
    return true;
  }
  return groupKey != null;
}

export function resolvePageTitle(context: DocumentTitleContext): string {
  const searchParams = new URLSearchParams(context.search ?? "");
  const groupKey = searchParams.get("group");
  const operationKey = context.dataOperationKey ?? searchParams.get("operation");

  switch (context.route) {
    case "/login":
      return authLabels.pageTitle;
    case "/dashboard":
      return dashboardLabels.pageTitle;
    case "/customers":
      return labels.customers;
    case "/customers/:id":
      return context.customerName?.trim() || labels.customers;
    case "/fairs":
      return fairLabels.fairs;
    case "/fairs/:id":
      return context.fairName?.trim() || fairLabels.fairs;
    case "/fairs/:id/enrichment":
      return fairLabels.enrichFairAction;
    case "/todos":
      return todoLabels.pageTitle;
    case "/todos/:id":
      return context.todoTitle?.trim() || todoLabels.pageTitle;
    case "/operations":
      return uiLabels.navOperations;
    case "/operations/new/scraper":
      return operationLabels.scraperWizardTitle;
    case "/operations/:id":
      return operationLabels.detailTitle;
    case "/follow-ups":
      return followUpLabels.pageTitle;
    case "/activities":
      return activityLabels.pageTitle;
    case "/data-integration/imports":
      return dataIntegrationLabels.importsTitle;
    case "/data-integration/imports/new":
    case "/data-integration/imports/fair/:fairId":
    case "/data-integration/imports/continue/:batchId":
    case "/imports":
    case "/imports/fair/:fairId":
      return importLabels.wizardTitle;
    case "/data-integration/adapters":
      return scraperLabels.pageTitle;
    case "/data-integration/adapters/:adapterKey":
      return (
        context.adapterName?.trim() ||
        context.adapterKey?.trim() ||
        scraperLabels.pageTitle
      );
    case "/data-integration/run-history":
      return scraperLabels.runHistoryTitle;
    case "/data-integration/runs/:runId":
      return scraperLabels.enrichmentRunDetailTitle;
    case "/data-integration/scraper-test":
      return scraperLabels.testPageTitle;
    case "/data-integration/enrichment":
      return dataIntegrationLabels.enrichmentTitle;
    case "/data-integration/jobs":
      return dataIntegrationLabels.navJobs;
    case "/data-integration/reports":
      return dataIntegrationLabels.navReports;
    case "/admin/system/backups":
      return adminLabels.backupsTitle;
    case "/admin/smtp-operations/accounts":
      return adminLabels.smtpTitle;
    case "/admin/smtp-operations/templates":
      return adminLabels.mailTemplatesTitle;
    case "/admin/smtp-operations/mail-operations":
      return adminLabels.mailOperationsTitle;
    case "/admin/data-operations":
      return adminLabels.dataOperationsTitle;
    case "/admin/data-operations/runs/:runId":
      if (isDuplicateDataOperationRoute(operationKey, groupKey)) {
        return groupKey
          ? adminLabels.dataOpDuplicateGroupDetailTitle
          : adminLabels.dataOpDuplicateGroupsTitle;
      }
      return adminLabels.dataOpAnalyzeResultTitle;
    case "/admin/operation-capabilities":
      return adminLabels.operationCapabilitiesTitle;
    default:
      return labels.customers;
  }
}

export function applyDocumentTitle(context: DocumentTitleContext): void {
  document.title = formatDocumentTitle(resolvePageTitle(context));
}
