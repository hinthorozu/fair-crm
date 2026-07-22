import React from "react";
import { getFair, archiveFair, updateFair, runFairScraper } from "../api/fairs";
import { getScraperRun, listAdapters, listScraperRuns } from "../api/scraper";
import {
  createParticipation,
  deleteParticipation,
  listParticipantsByFair,
  updateParticipation,
} from "../api/participations";
import { listCustomers } from "../api/customers";
import { ApiError } from "../api/client";
import { FairParticipantTable } from "../components/ParticipationList";
import {
  ParticipationForm,
  fairParticipantToFormValues,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
  type ParticipationFormValues,
} from "../components/ParticipationForm";
import { FairBulkEmailWizard } from "../components/fairs/FairBulkEmailWizard";
import { FairBulkEmailBatchLogs } from "../components/fairs/FairBulkEmailBatchLogs";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { FormModal, TextInput } from "../components/ui/form";
import { FairForm, fairToFormValues } from "../components/FairForm";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { TabPanel, Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { SectionHeader } from "../components/ui/SectionHeader";
import {
  DetailDate,
  DetailValue,
  DetailWebsite,
} from "../components/ui/DetailFields";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { participationLabels } from "../labels/participationLabels";
import { importLabels } from "../labels/importLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import type { Customer } from "../types/customer";
import type { CreateFairPayload, Fair } from "../types/fair";
import type { SendBulkEmailResponse } from "../types/fairBulkEmail";
import type { AdapterListItem } from "../types/scraper";
import { formatAdapterOptionLabel } from "../utils/fairIntegration";
import type { FairParticipantListItem } from "../types/participation";
import { DEFAULT_PAGE } from "../types/listTable";
import {
  canPerformFairEmailAction,
  getGrantedFairEmailPermissions,
} from "../permissions/fairEmailPermissions";
import {
  canRunScraperActions,
  getGrantedScraperPermissions,
} from "../permissions/scraperPermissions";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";
import {
  buildLocationSearch,
  navigateWithSearch,
  readSearchParams,
} from "../utils/urlState";

interface FairDetailPageProps {
  fairId: string;
  onBack: () => void;
  onFairLoaded?: (name: string) => void;
  onOpenCustomer?: (customerId: string) => void;
  onImportParticipants?: () => void;
  onOpenImportDecisions?: (batchId: string) => void;
  onOpenFairEnrichment?: (fairId: string) => void;
}

type TabId = "overview" | "participants";

const VALID_TABS: TabId[] = ["overview", "participants"];

function tabFromUrl(): TabId {
  const tab = readSearchParams().get("tab");
  if (tab && VALID_TABS.includes(tab as TabId)) return tab as TabId;
  return "overview";
}

export function FairDetailPage({
  fairId,
  onBack,
  onFairLoaded,
  onOpenCustomer,
  onImportParticipants,
  onOpenImportDecisions,
  onOpenFairEnrichment,
}: FairDetailPageProps) {
  const [fair, setFair] = React.useState<Fair | null>(null);
  const [customers, setCustomers] = React.useState<Customer[]>([]);
  const [activeTab, setActiveTabState] = React.useState<TabId>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"edit-fair" | "create" | "edit" | "bulk-email" | null>(null);
  const [editing, setEditing] = React.useState<FairParticipantListItem | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<FairParticipantListItem | null>(null);
  const [confirmArchive, setConfirmArchive] = React.useState(false);
  const [participantCount, setParticipantCount] = React.useState(0);
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [runningScraper, setRunningScraper] = React.useState(false);
  const [runSuccess, setRunSuccess] = React.useState<string | null>(null);
  const [lastImportAt, setLastImportAt] = React.useState<string | null>(null);
  const [logsRefreshToken, setLogsRefreshToken] = React.useState(0);
  const [highlightBatchId, setHighlightBatchId] = React.useState<string | null>(null);

  const detailPath = `/fairs/${fairId}`;

  const participantsTable = useServerDataTable<FairParticipantListItem>({
    fetchFn: (params) => listParticipantsByFair(fairId, params),
    defaultSort: { field: "company_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: activeTab === "participants" && Boolean(fair),
  });

  const setActiveTab = React.useCallback(
    (tab: TabId) => {
      setActiveTabState(tab);
      const params = readSearchParams();
      if (tab === "overview") params.delete("tab");
      else params.set("tab", tab);
      navigateWithSearch(detailPath, buildLocationSearch(params));
    },
    [detailPath],
  );

  const loadLastImport = React.useCallback(async (id: string) => {
    try {
      const response = await listScraperRuns({ fair_id: id, limit: 20 });
      const latestCompleted = response.items.find(
        (run) => run.status === "completed" && run.finished_at,
      );
      setLastImportAt(latestCompleted?.finished_at ?? null);
    } catch {
      // best-effort
    }
  }, []);

  const loadFair = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFair(fairId);
      setFair(data);
      onFairLoaded?.(data.name);
      void loadLastImport(fairId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Fuar yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [fairId, loadLastImport, onFairLoaded]);

  const loadCustomersForForm = React.useCallback(async () => {
    try {
      const res = await listCustomers({ page: 1, pageSize: 100, status: "active" });
      setCustomers(res.items);
    } catch {
      // best-effort
    }
  }, []);

  React.useEffect(() => {
    void loadFair();
  }, [loadFair]);

  React.useEffect(() => {
    void listAdapters()
      .then((response) => setAdapters(response.items))
      .catch(() => {
        // Adapter labels fall back to adapter_key on detail view.
      });
  }, []);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  React.useEffect(() => {
    if (!fair) return;
    void listParticipantsByFair(fairId, { page: 1, pageSize: 1 }).then((res) => {
      setParticipantCount(res.pagination.totalItems);
    });
  }, [fairId, fair]);

  React.useEffect(() => {
    if (activeTab === "participants") {
      setParticipantCount(participantsTable.pagination.totalItems);
    }
  }, [activeTab, participantsTable.pagination.totalItems]);

  React.useEffect(() => {
    if (activeTab === "participants") {
      void loadCustomersForForm();
    }
  }, [activeTab, loadCustomersForForm]);

  const closeModal = React.useCallback(() => setModal(null), []);
  const closeConfirmDelete = React.useCallback(() => setConfirmDelete(null), []);
  const closeConfirmArchive = React.useCallback(() => setConfirmArchive(false), []);

  const handleBulkEmailSent = React.useCallback((result: SendBulkEmailResponse) => {
    setRunSuccess(result.message || fairLabels.bulkEmailSuccess);
    setLogsRefreshToken((value) => value + 1);
    setHighlightBatchId(result.batch_id);
    setModal(null);
  }, []);

  const handleCreate = async (values: ParticipationFormValues) => {
    await createParticipation(formValuesToCreatePayload(values, "fair", fairId));
    setModal(null);
    await participantsTable.refresh();
  };

  const handleUpdate = async (values: ParticipationFormValues) => {
    if (!editing) return;
    await updateParticipation(editing.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditing(null);
    await participantsTable.refresh();
  };

  const handleDelete = async (item: FairParticipantListItem) => {
    setDeletingId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      await participantsTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingId(null);
      setConfirmDelete(null);
    }
  };

  const participantTotal = participantCount;

  const handleUpdateFair = async (values: CreateFairPayload) => {
    await updateFair(fairId, values);
    setModal(null);
    await loadFair();
  };

  const adapterDisplay = React.useMemo(() => {
    if (!fair?.adapter_key) return null;
    const match = adapters.find((adapter) => adapter.adapter_key === fair.adapter_key);
    if (match) {
      return formatAdapterOptionLabel(match.display_name, match.adapter_key);
    }
    return fair.adapter_key;
  }, [adapters, fair?.adapter_key]);

  const scraperConfigDisplay = React.useMemo(() => {
    if (!fair?.scraper_config || Object.keys(fair.scraper_config).length === 0) {
      return null;
    }
    return JSON.stringify(fair.scraper_config, null, 2);
  }, [fair?.scraper_config]);

  const fairEmailPermissions = React.useMemo(() => getGrantedFairEmailPermissions(), []);
  const scraperPermissions = React.useMemo(() => getGrantedScraperPermissions(), []);
  const canPreviewFairEmail = canPerformFairEmailAction(fairEmailPermissions, "preview");
  const canSendFairEmail = canPerformFairEmailAction(fairEmailPermissions, "send");
  const canRunEnrichment = canRunScraperActions(scraperPermissions);

  const canRunScraper =
    Boolean(fair?.adapter_key?.trim() && fair?.source_url?.trim()) &&
    fair?.status !== "archived" &&
    fair?.deleted_at == null;

  const pollScraperRun = React.useCallback(
    async (runId: string): Promise<{ importBatchId: string | null; totalRows: number }> => {
      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        const run = await getScraperRun(runId);
        if (run.status === "completed") {
          setLastImportAt(run.finished_at);
          return {
            importBatchId: run.import_batch_id ?? null,
            totalRows: run.total_rows ?? 0,
          };
        }
        if (run.status === "failed") {
          throw new ApiError(run.error_message || fairLabels.runScraperError, 500);
        }
      }
      throw new ApiError(fairLabels.runScraperError, 504);
    },
    [],
  );

  const handleRunScraper = async () => {
    setRunningScraper(true);
    setRunSuccess(null);
    setError(null);
    try {
      const run = await runFairScraper(fairId);
      setRunSuccess(fairLabels.runScraperRunning);
      const result = await pollScraperRun(run.id);
      if (result.importBatchId && onOpenImportDecisions) {
        setRunSuccess(fairLabels.runScraperComplete);
        onOpenImportDecisions(result.importBatchId);
        return;
      }
      if (result.totalRows === 0) {
        setRunSuccess(fairLabels.runScraperNoRows);
        return;
      }
      setRunSuccess(fairLabels.runScraperSuccess);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.runScraperError);
    } finally {
      setRunningScraper(false);
    }
  };

  const openFairEnrichment = () => {
    if (!canRunEnrichment) {
      setError(fairLabels.enrichFairPermissionDenied);
      return;
    }
    onOpenFairEnrichment?.(fairId);
  };

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    {
      id: "participants" as const,
      label: participationLabels.tabFairParticipants,
      badge: participantTotal > 0 ? participantTotal : undefined,
    },
  ];

  if (loading) {
    return <LoadingState />;
  }

  if (!fair) {
    return (
      <PageShell>
        <Banner variant="error">{error ?? "Fuar bulunamadı."}</Banner>
        <button type="button" className="btn secondary" onClick={onBack}>
          ← {fairLabels.fairs}
        </button>
      </PageShell>
    );
  }

  const handleArchiveFair = async () => {
    setArchiving(true);
    setError(null);
    try {
      await archiveFair(fairId);
      setConfirmArchive(false);
      onBack();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.archiveError);
    } finally {
      setArchiving(false);
    }
  };

  const openCreateParticipant = () => {
    void loadCustomersForForm();
    setEditing(null);
    setModal("create");
  };

  const isArchived = fair.status === "archived" || fair.deleted_at !== null;

  const headerActions: PageHeaderAction[] = [
    {
      id: "edit",
      label: uiLabels.detailEdit,
      variant: "primary",
      onClick: () => setModal("edit-fair"),
      disabled: isArchived,
    },
    {
      id: "add-participant",
      label: participationLabels.addCompany,
      variant: "secondary",
      onClick: openCreateParticipant,
      disabled: isArchived,
    },
    {
      id: "import",
      label: importLabels.importFromFair,
      variant: "secondary",
      onClick: () => onImportParticipants?.(),
      disabled: isArchived || !onImportParticipants,
    },
    {
      id: "enrich",
      label: fairLabels.enrichFairAction,
      variant: "secondary",
      onClick: openFairEnrichment,
      disabled: isArchived || !canRunEnrichment || !onOpenFairEnrichment,
      title: !canRunEnrichment ? fairLabels.enrichFairPermissionDenied : undefined,
    },
    {
      id: "activity",
      label: uiLabels.detailNewActivity,
      variant: "secondary",
      disabled: true,
      title: uiLabels.detailFairActivitySoon,
      onClick: () => undefined,
    },
    {
      id: "archive",
      label: labels.archive,
      variant: "danger",
      onClick: () => setConfirmArchive(true),
      disabled: isArchived,
      loading: archiving,
    },
  ];

  return (
    <PageShell>
      <PageHeader
        title={fair.name}
        subtitle={
          <Badge variant={fair.status === "archived" ? "danger" : "info"}>
            {fairStatusLabels[fair.status] ?? fair.status}
          </Badge>
        }
        breadcrumbs={[{ label: uiLabels.backToFairs, onClick: onBack }]}
        actions={headerActions}
      />

      <Tabs items={tabItems} active={activeTab} onChange={setActiveTab} />

      {runSuccess && <Banner variant="success">{runSuccess}</Banner>}
      {error && <Banner variant="error">{error}</Banner>}

      <TabPanel id="panel-fair-overview" labelledBy="tab-overview" active={activeTab === "overview"}>
        <Card>
          <dl className="detail-grid">
            <div>
              <dt>{fairLabels.name}</dt>
              <dd>{fair.name}</dd>
            </div>
            <div>
              <dt>{labels.status}</dt>
              <dd>{fairStatusLabels[fair.status] ?? fair.status}</dd>
            </div>
            <div>
              <dt>{fairLabels.organizer}</dt>
              <dd>
                <DetailValue value={fair.organizer} />
              </dd>
            </div>
            <div>
              <dt>{fairLabels.venue}</dt>
              <dd>
                <DetailValue value={fair.venue} />
              </dd>
            </div>
            <div>
              <dt>{labels.website}</dt>
              <dd>
                <DetailWebsite value={fair.website} />
              </dd>
            </div>
            <div>
              <dt>{labels.country}</dt>
              <dd>
                <DetailValue value={fair.country} />
              </dd>
            </div>
            <div>
              <dt>{labels.city}</dt>
              <dd>
                <DetailValue value={fair.city} />
              </dd>
            </div>
            <div>
              <dt>{fairLabels.start_date}</dt>
              <dd>
                <DetailDate value={fair.start_date} />
              </dd>
            </div>
            <div>
              <dt>{fairLabels.end_date}</dt>
              <dd>
                <DetailDate value={fair.end_date} />
              </dd>
            </div>
            <div className="full-width">
              <dt>{labels.description}</dt>
              <dd className="detail-multiline">
                <DetailValue value={fair.description} />
              </dd>
            </div>
          </dl>
        </Card>

        <Card className="detail-card-spaced">
          <SectionHeader
            title={fairLabels.dataIntegration}
            actions={
              <button
                type="button"
                className="btn primary"
                disabled={!canRunScraper || runningScraper}
                onClick={() => void handleRunScraper()}
              >
                {runningScraper ? fairLabels.runScraperRunning : fairLabels.runScraper}
              </button>
            }
          />
          <dl className="detail-grid">
            <div>
              <dt>{fairLabels.adapter}</dt>
              <dd>
                <DetailValue value={adapterDisplay} />
              </dd>
            </div>
            <div>
              <dt>{fairLabels.sourceUrl}</dt>
              <dd>
                <DetailWebsite value={fair.source_url} />
              </dd>
            </div>
            <div>
              <dt>{fairLabels.lastImport}</dt>
              <dd>
                <DetailDate value={lastImportAt} />
              </dd>
            </div>
            <div className="full-width">
              <dt>{fairLabels.scraperConfig}</dt>
              <dd className="detail-multiline">
                <DetailValue value={scraperConfigDisplay} />
              </dd>
            </div>
          </dl>
        </Card>

        <Card className="detail-card-spaced">
          <SectionHeader
            title={fairLabels.bulkEmailCardTitle}
            actions={
              canPreviewFairEmail ? (
                <button
                  type="button"
                  className="btn primary"
                  disabled={isArchived}
                  onClick={() => setModal("bulk-email")}
                >
                  {fairLabels.bulkEmailStartAction}
                </button>
              ) : undefined
            }
          />
          {canPreviewFairEmail ? (
            <p className="text-muted">{fairLabels.bulkEmailCardDescription}</p>
          ) : (
            <Banner variant="warning">{fairLabels.bulkEmailPermissionPreviewDeniedDebug}</Banner>
          )}
        </Card>

        <Card className="detail-card-spaced">
          <FairBulkEmailBatchLogs
            fairId={fairId}
            canView={canPreviewFairEmail}
            refreshToken={logsRefreshToken}
            highlightBatchId={highlightBatchId}
          />
        </Card>
      </TabPanel>

      <TabPanel id="panel-participants" labelledBy="tab-participants" active={activeTab === "participants"}>
        <ServerDataTableFrame
          table={participantsTable}
          skeletonCols={8}
          toolbar={
            <FilterPanel
              actions={
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => void participantsTable.refresh()}
                >
                  {labels.refresh}
                </button>
              }
            >
              <TextInput
                id="fair-participants-search"
                type="search"
                className="search-input"
                placeholder={uiLabels.searchCustomer}
                value={participantsTable.search}
                onChange={(e) => participantsTable.setSearch(e.target.value)}
                aria-label={uiLabels.searchCustomer}
              />
            </FilterPanel>
          }
        >
          <FairParticipantTable
            items={participantsTable.items}
            deletingId={deletingId}
            emptyDueToFilters={participantsTable.hasActiveFilters}
            sortField={participantsTable.sorting.field}
            sortDirection={participantsTable.sorting.direction}
            onSortChange={participantsTable.setSort}
            onCreate={openCreateParticipant}
            onEdit={(item) => {
              setEditing(item);
              setModal("edit");
            }}
            onDelete={(item) => setConfirmDelete(item)}
            onOpenCustomer={onOpenCustomer}
          />
        </ServerDataTableFrame>
      </TabPanel>

      {modal === "edit-fair" && (
        <FormModal title={fairLabels.editFair} onClose={closeModal} size="lg">
          <FairForm
            key={fair.id}
            initial={fairToFormValues(fair)}
            submitLabel={labels.save}
            onCancel={closeModal}
            onSubmit={handleUpdateFair}
          />
        </FormModal>
      )}

      {modal === "create" && (
        <FormModal title={participationLabels.newParticipant} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="fair"
            customers={customers}
            submitLabel={participationLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreate}
          />
        </FormModal>
      )}

      {modal === "edit" && editing && (
        <FormModal title={participationLabels.editParticipant} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="fair"
            customers={customers}
            initial={fairParticipantToFormValues(editing, editing.customer_id)}
            submitLabel={participationLabels.save}
            onCancel={closeModal}
            onSubmit={handleUpdate}
          />
        </FormModal>
      )}

      {modal === "bulk-email" && (
        <FormModal title={fairLabels.bulkEmailModalTitle} onClose={closeModal} size="lg">
          <FairBulkEmailWizard
            fair={fair}
            canPreview={canPreviewFairEmail}
            canSend={canSendFairEmail}
            onCancel={closeModal}
            onSent={handleBulkEmailSent}
          />
        </FormModal>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={uiLabels.delete}
          message={participationLabels.deleteConfirm}
          confirmLabel={uiLabels.delete}
          variant="danger"
          loading={deletingId === confirmDelete.id}
          onCancel={closeConfirmDelete}
          onConfirm={() => void handleDelete(confirmDelete)}
        />
      )}

      {confirmArchive && (
        <ConfirmDialog
          title={labels.archive}
          message={fairLabels.archiveConfirm}
          confirmLabel={labels.archive}
          variant="danger"
          loading={archiving}
          onCancel={closeConfirmArchive}
          onConfirm={() => void handleArchiveFair()}
        />
      )}
    </PageShell>
  );
}
