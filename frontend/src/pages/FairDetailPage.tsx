import React from "react";
import { compareSystemFairImport, getFair, archiveFair, runFairScraper, updateFair } from "../api/fairs";
import { listAdapters, listScraperRuns } from "../api/scraper";
import {
  createParticipation,
  deleteParticipation,
  listParticipantsByFair,
  moveParticipantsToFair,
  updateParticipation,
} from "../api/participations";
import { ApiError } from "../api/client";
import { FairParticipantTable } from "../components/ParticipationList";
import {
  ParticipationForm,
  fairParticipantToFormValues,
  formValuesToCreatePayload,
  formValuesToUpdatePayload,
  type ParticipationFormValues,
} from "../components/ParticipationForm";
import { MoveCustomersToFairModal } from "../components/MoveCustomersToFairModal";
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
import { usePermissions } from "../hooks/usePermissions";
import { useAuth } from "../auth/AuthContext";
import { useServerDataTable } from "../hooks/useServerDataTable";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { participationLabels } from "../labels/participationLabels";
import { importLabels } from "../labels/importLabels";
import { uiLabels } from "../labels/uiLabels";
import { labels } from "../labels";
import { systemFairScrapeReady, type CreateFairPayload, type Fair } from "../types/fair";
import type { SendBulkEmailResponse } from "../types/fairBulkEmail";
import type { AdapterListItem } from "../types/scraper";
import { formatAdapterOptionLabel } from "../utils/fairIntegration";
import type { FairParticipantListItem } from "../types/participation";
import { DEFAULT_PAGE } from "../types/listTable";
import {
  canPerformFairEmailAction,
  getGrantedFairEmailPermissions,
} from "../permissions/fairEmailPermissions";
import { FAIR_DELETE, FAIR_UPDATE } from "../permissions/fairPermissions";
import {
  PARTICIPATION_CREATE,
  PARTICIPATION_DELETE,
  PARTICIPATION_READ,
  PARTICIPATION_UPDATE,
} from "../permissions/participationPermissions";
import {
  PERMISSION_IMPORTS_CREATE,
  PERMISSION_SCRAPER_READ,
} from "../permissions/navigationPermissions";
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
  onContinueImport?: (batchId: string) => void;
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
  onContinueImport,
}: FairDetailPageProps) {
  const { session } = useAuth();
  const isSuperAdmin = session?.isSuperAdmin === true;
  const { can } = usePermissions();
  const canUpdateFair = can(FAIR_UPDATE);
  const canDeleteFair = can(FAIR_DELETE);
  const canReadParticipants = can(PARTICIPATION_READ);
  const canCreateParticipation = can(PARTICIPATION_CREATE);
  const canUpdateParticipation = can(PARTICIPATION_UPDATE);
  const canDeleteParticipation = can(PARTICIPATION_DELETE);
  const canImportParticipants = can(PERMISSION_IMPORTS_CREATE);
  const canReadScraper = can(PERMISSION_SCRAPER_READ);

  const [fair, setFair] = React.useState<Fair | null>(null);
  const [activeTab, setActiveTabState] = React.useState<TabId>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<
    "edit-fair" | "create" | "edit" | "bulk-email" | "move-customers" | null
  >(null);
  const [editing, setEditing] = React.useState<FairParticipantListItem | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<FairParticipantListItem | null>(null);
  const [confirmArchive, setConfirmArchive] = React.useState(false);
  const [participantCount, setParticipantCount] = React.useState(0);
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [runSuccess, setRunSuccess] = React.useState<string | null>(null);
  const [comparing, setComparing] = React.useState(false);
  const [scraperRunning, setScraperRunning] = React.useState(false);
  const comparingRef = React.useRef(false);
  const scraperRunningRef = React.useRef(false);
  const [lastImportAt, setLastImportAt] = React.useState<string | null>(null);
  const [logsRefreshToken, setLogsRefreshToken] = React.useState(0);
  const [highlightBatchId, setHighlightBatchId] = React.useState<string | null>(null);
  const [moveTargetFairId, setMoveTargetFairId] = React.useState("");
  const [movingCustomers, setMovingCustomers] = React.useState(false);

  const detailPath = `/fairs/${fairId}`;

  const participantsTable = useServerDataTable<FairParticipantListItem>({
    fetchFn: (params) => listParticipantsByFair(fairId, params),
    defaultSort: { field: "company_name", direction: "asc" },
    urlSync: true,
    urlPath: detailPath,
    enabled: canReadParticipants && activeTab === "participants" && Boolean(fair),
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

  React.useEffect(() => {
    if (!canReadParticipants && activeTab === "participants") {
      setActiveTab("overview");
    }
  }, [activeTab, canReadParticipants, setActiveTab]);

  const loadLastImport = React.useCallback(
    async (id: string) => {
      if (!canReadScraper) {
        setLastImportAt(null);
        return;
      }
      try {
        const response = await listScraperRuns({ fair_id: id, limit: 20 });
        const latestCompleted = response.items.find(
          (run) => run.status === "completed" && run.finished_at,
        );
        setLastImportAt(latestCompleted?.finished_at ?? null);
      } catch {
        // best-effort
      }
    },
    [canReadScraper],
  );

  const loadFair = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFair(fairId);
      setFair(data);
      onFairLoaded?.(data.name);
      if (data.origin === "system") {
        setLastImportAt(null);
      } else {
        void loadLastImport(fairId);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Fuar yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [fairId, loadLastImport, onFairLoaded]);

  React.useEffect(() => {
    void loadFair();
  }, [loadFair]);

  React.useEffect(() => {
    if (!canReadScraper) {
      setAdapters([]);
      return;
    }
    void listAdapters()
      .then((response) => setAdapters(response.items))
      .catch(() => {
        // Adapter labels fall back to adapter_key on detail view.
      });
  }, [canReadScraper]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const refreshParticipantCount = React.useCallback(async () => {
    if (!canReadParticipants) {
      setParticipantCount(0);
      return;
    }
    const res = await listParticipantsByFair(fairId, { page: 1, pageSize: 1 });
    setParticipantCount(res.pagination.totalItems);
  }, [canReadParticipants, fairId]);

  React.useEffect(() => {
    if (!fair) return;
    void refreshParticipantCount().catch(() => {
      // best-effort count
    });
  }, [fair, refreshParticipantCount]);

  React.useEffect(() => {
    if (canReadParticipants && activeTab === "participants") {
      setParticipantCount(participantsTable.pagination.totalItems);
    }
  }, [activeTab, canReadParticipants, participantsTable.pagination.totalItems]);

  const closeModal = React.useCallback(() => {
    setModal(null);
    setMoveTargetFairId("");
  }, []);
  const closeConfirmDelete = React.useCallback(() => setConfirmDelete(null), []);
  const closeConfirmArchive = React.useCallback(() => setConfirmArchive(false), []);

  const handleMoveCustomers = async () => {
    if (!canUpdateParticipation || !moveTargetFairId) return;
    setMovingCustomers(true);
    setError(null);
    try {
      await moveParticipantsToFair(fairId, moveTargetFairId);
      setModal(null);
      setMoveTargetFairId("");
      setRunSuccess(fairLabels.moveCustomersSuccess);
      await refreshParticipantCount();
      if (canReadParticipants && activeTab === "participants") {
        await participantsTable.refresh();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.moveCustomersError);
    } finally {
      setMovingCustomers(false);
    }
  };

  const handleBulkEmailSent = React.useCallback((result: SendBulkEmailResponse) => {
    setRunSuccess(result.message || fairLabels.bulkEmailSuccess);
    setLogsRefreshToken((value) => value + 1);
    setHighlightBatchId(result.batch_id);
    setModal(null);
  }, []);

  const handleCreate = async (values: ParticipationFormValues) => {
    if (!canCreateParticipation) return;
    await createParticipation(formValuesToCreatePayload(values, "fair", fairId));
    setModal(null);
    if (canReadParticipants) await participantsTable.refresh();
  };

  const handleUpdate = async (values: ParticipationFormValues) => {
    if (!canUpdateParticipation || !editing) return;
    await updateParticipation(editing.id, formValuesToUpdatePayload(values));
    setModal(null);
    setEditing(null);
    if (canReadParticipants) await participantsTable.refresh();
  };

  const handleDelete = async (item: FairParticipantListItem) => {
    if (!canDeleteParticipation) return;
    setDeletingId(item.id);
    setError(null);
    try {
      await deleteParticipation(item.id);
      if (canReadParticipants) await participantsTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : participationLabels.deleteError);
    } finally {
      setDeletingId(null);
      setConfirmDelete(null);
    }
  };

  const participantTotal = participantCount;

  const handleUpdateFair = async (values: CreateFairPayload) => {
    if (!canUpdateFair) return;
    if (fair?.origin === "system" && !isSuperAdmin) return;
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
  const canPreviewFairEmail = canPerformFairEmailAction(fairEmailPermissions, "preview");
  const canSendFairEmail = canPerformFairEmailAction(fairEmailPermissions, "send");

  const tabItems = [
    { id: "overview" as const, label: uiLabels.tabOverview },
    ...(canReadParticipants
      ? [
          {
            id: "participants" as const,
            label: participationLabels.tabFairParticipants,
            badge: participantTotal > 0 ? participantTotal : undefined,
          },
        ]
      : []),
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
    if (!canDeleteFair) return;
    if (fair.origin === "system") return;
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
    if (!canCreateParticipation) return;
    setEditing(null);
    setModal("create");
  };

  const isArchived = fair.status === "archived" || fair.deleted_at !== null;
  const isSystemFair = fair.origin === "system";
  const canManageSystemFair = !isSystemFair || isSuperAdmin;
  const compareReady = systemFairScrapeReady(fair);

  const handleCompare = async () => {
    if (comparingRef.current) return;
    if (!isSystemFair || !compareReady) return;
    comparingRef.current = true;
    setComparing(true);
    setError(null);
    try {
      const result = await compareSystemFairImport(fair.id);
      onContinueImport?.(result.batch_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.compareError);
    } finally {
      comparingRef.current = false;
      setComparing(false);
    }
  };

  const handleRunScraper = async () => {
    if (scraperRunningRef.current) return;
    if (!isSystemFair || !isSuperAdmin) return;
    scraperRunningRef.current = true;
    setScraperRunning(true);
    setError(null);
    setRunSuccess(null);
    try {
      await runFairScraper(fair.id);
      setRunSuccess(fairLabels.runScraperSuccess);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.runScraperError);
    } finally {
      scraperRunningRef.current = false;
      setScraperRunning(false);
    }
  };

  const headerActions: PageHeaderAction[] = [];
  if (isSystemFair) {
    headerActions.push({
      id: "compare-import",
      label: fairLabels.compareWithCrm,
      variant: canManageSystemFair ? "secondary" : "primary",
      onClick: () => void handleCompare(),
      disabled: !compareReady,
      loading: comparing,
      title: compareReady ? undefined : fairLabels.compareUnavailable,
    });
  }
  if (canUpdateFair) {
    if (canManageSystemFair) {
      headerActions.push({
        id: "edit",
        label: uiLabels.detailEdit,
        variant: "primary",
        onClick: () => setModal("edit-fair"),
        disabled: isArchived,
      });
    }
  }
  if (canCreateParticipation) {
    headerActions.push({
      id: "add-participant",
      label: participationLabels.addCompany,
      variant: "secondary",
      onClick: openCreateParticipant,
      disabled: isArchived,
    });
  }
  if (canUpdateParticipation) {
    if (!isSystemFair) {
      headerActions.push({
        id: "move-customers",
        label: fairLabels.moveCustomersAction,
        variant: "secondary",
        onClick: () => {
          setMoveTargetFairId("");
          setModal("move-customers");
        },
        disabled: isArchived,
      });
    }
  }
  if (canImportParticipants) {
    if (!isSystemFair) {
      headerActions.push({
        id: "import",
        label: importLabels.importFromFair,
        variant: "secondary",
        onClick: () => onImportParticipants?.(),
        disabled: isArchived || !onImportParticipants,
      });
    }
  }
  if (isSystemFair && isSuperAdmin) {
    headerActions.push({
      id: "run-scraper",
      label: fairLabels.runSystemScraper,
      variant: "secondary",
      onClick: () => void handleRunScraper(),
      disabled: isArchived,
      loading: scraperRunning,
    });
  }
  headerActions.push({
    id: "activity",
    label: uiLabels.detailNewActivity,
    variant: "secondary",
    disabled: true,
    title: uiLabels.detailFairActivitySoon,
    onClick: () => undefined,
  });
  if (canDeleteFair) {
    if (!isSystemFair) {
      headerActions.push({
        id: "archive",
        label: labels.archive,
        variant: "danger",
        onClick: () => setConfirmArchive(true),
        disabled: isArchived,
        loading: archiving,
      });
    }
  }

  return (
    <PageShell>
      <PageHeader
        title={fair.display_name}
        subtitle={
          <>
            <Badge variant={fair.status === "archived" ? "danger" : "info"}>
              {fairStatusLabels[fair.status] ?? fair.status}
            </Badge>
            {isSystemFair && <Badge variant="neutral">{fairLabels.systemFair}</Badge>}
          </>
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
              <dt>{fair.display_name === fair.name ? fairLabels.name : fairLabels.officialName}</dt>
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
            {isSystemFair && (
              <>
                <div>
                  <dt>{fairLabels.scrapedRecordCount}</dt>
                  <dd>
                    {fair.scraped_record_count != null ? `${fair.scraped_record_count} kayıt` : "—"}
                  </dd>
                </div>
                <div>
                  <dt>{fairLabels.scrapedAt}</dt>
                  <dd>
                    <DetailDate value={fair.scraped_at} />
                  </dd>
                </div>
              </>
            )}
            <div className="full-width">
              <dt>{labels.description}</dt>
              <dd className="detail-multiline">
                <DetailValue value={fair.description} />
              </dd>
            </div>
          </dl>
        </Card>

        {(fair.origin !== "system" || isSuperAdmin) && (
        <Card className="detail-card-spaced">
          <SectionHeader title={fairLabels.dataIntegration} />
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
            {fair.origin !== "system" && (
              <div>
                <dt>{fairLabels.lastImport}</dt>
                <dd>
                  <DetailDate value={lastImportAt} />
                </dd>
              </div>
            )}
            <div className="full-width">
              <dt>{fairLabels.scraperConfig}</dt>
              <dd className="detail-multiline">
                <DetailValue value={scraperConfigDisplay} />
              </dd>
            </div>
          </dl>
        </Card>
        )}

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

      {canReadParticipants && (
        <TabPanel
          id="panel-participants"
          labelledBy="tab-participants"
          active={activeTab === "participants"}
        >
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
              onCreate={canCreateParticipation ? openCreateParticipant : undefined}
              onEdit={
                canUpdateParticipation
                  ? (item) => {
                      setEditing(item);
                      setModal("edit");
                    }
                  : undefined
              }
              onDelete={canDeleteParticipation ? (item) => setConfirmDelete(item) : undefined}
              onOpenCustomer={onOpenCustomer}
            />
          </ServerDataTableFrame>
        </TabPanel>
      )}

      {modal === "edit-fair" && canUpdateFair && canManageSystemFair && (
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

      {modal === "create" && canCreateParticipation && (
        <FormModal title={participationLabels.newParticipant} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="fair"
            submitLabel={participationLabels.save}
            onCancel={closeModal}
            onSubmit={handleCreate}
          />
        </FormModal>
      )}

      {modal === "edit" && editing && canUpdateParticipation && (
        <FormModal title={participationLabels.editParticipant} onClose={closeModal} size="lg">
          <ParticipationForm
            mode="fair"
            hydrateKey={editing.id}
            initial={fairParticipantToFormValues(editing, editing.customer_id)}
            lockCustomer
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

      <MoveCustomersToFairModal
        open={canUpdateParticipation && modal === "move-customers" && fair.origin !== "system"}
        sourceFairId={fairId}
        targetFairId={moveTargetFairId}
        moving={movingCustomers}
        onTargetFairChange={setMoveTargetFairId}
        onClose={closeModal}
        onConfirm={() => void handleMoveCustomers()}
      />

      {confirmDelete && canDeleteParticipation && (
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

      {confirmArchive && canDeleteFair && fair.origin !== "system" && (
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
