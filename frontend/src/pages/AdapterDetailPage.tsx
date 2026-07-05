import React from "react";
import {
  deleteAdapter,
  getAdapter,
  getAdapterDeletePreview,
  getScraperManifest,
  listScraperRuns,
  updateAdapterManifest,
} from "../api/scraper";
import { ApiError } from "../api/client";
import {
  AdapterDetailContent,
  type AdapterDetailTab,
} from "../components/scraper/AdapterDetailContent";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { scraperLabels } from "../labels/scraperLabels";
import { uiLabels } from "../labels/uiLabels";
import type { AdapterDeletePreview, AdapterListItem, ScraperManifest, ScraperRun } from "../types/scraper";
import {
  formStateToPayload,
  manifestToFormState,
  type AdapterEditFormState,
} from "../utils/adapterManifestForm";
import { adapterDetailToListItem } from "../utils/scraperAdapters";
import { buildLocationSearch, navigateWithSearch, readSearchParams } from "../utils/urlState";

interface AdapterDetailPageProps {
  adapterKey: string;
  onBack: () => void;
  onOpenFair?: (fairId: string) => void;
  onAdapterLoaded?: (displayName: string) => void;
  onViewAllRuns?: (adapterKey: string) => void;
  onOpenScraperTest?: (adapterKey: string, runId?: string) => void;
}

const VALID_TABS: AdapterDetailTab[] = ["manifest", "runs", "fairs"];
const EDITABLE_TABS: AdapterDetailTab[] = ["manifest"];

function tabFromUrl(): AdapterDetailTab {
  const tab = readSearchParams().get("tab");
  if (tab === "general" || tab === "console") return "manifest";
  if (tab && VALID_TABS.includes(tab as AdapterDetailTab)) return tab as AdapterDetailTab;
  return "manifest";
}

function resolveSaveError(err: unknown): string {
  if (!(err instanceof ApiError)) {
    return scraperLabels.manifestSaveError;
  }

  const body = err.body;
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return null;
        })
        .filter((message): message is string => Boolean(message));
      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }

  return err.message || scraperLabels.manifestSaveError;
}

export function AdapterDetailPage({
  adapterKey,
  onBack,
  onOpenFair,
  onAdapterLoaded,
  onViewAllRuns,
  onOpenScraperTest,
}: AdapterDetailPageProps) {
  const detailPath = `/data-integration/adapters/${encodeURIComponent(adapterKey)}`;
  const [adapterItem, setAdapterItem] = React.useState<AdapterListItem | null>(null);
  const [manifest, setManifest] = React.useState<ScraperManifest | null>(null);
  const [runs, setRuns] = React.useState<ScraperRun[]>([]);
  const [activeTab, setActiveTabState] = React.useState<AdapterDetailTab>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [manifestLoading, setManifestLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [manifestError, setManifestError] = React.useState<string | null>(null);
  const [isEditing, setIsEditing] = React.useState(false);
  const [draft, setDraft] = React.useState<AdapterEditFormState | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deletePreview, setDeletePreview] = React.useState<AdapterDeletePreview | null>(null);
  const [deletePreviewLoading, setDeletePreviewLoading] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  const onAdapterLoadedRef = React.useRef(onAdapterLoaded);
  onAdapterLoadedRef.current = onAdapterLoaded;

  const draftRef = React.useRef<AdapterEditFormState | null>(null);
  draftRef.current = draft;

  const isEditableTab = EDITABLE_TABS.includes(activeTab);

  const setActiveTab = React.useCallback(
    (tab: AdapterDetailTab) => {
      setActiveTabState(tab);
      const params = readSearchParams();
      if (tab === "manifest") params.delete("tab");
      else params.set("tab", tab);
      navigateWithSearch(detailPath, buildLocationSearch(params));
    },
    [detailPath],
  );

  const loadDetail = React.useCallback(async (options?: { showPageLoader?: boolean }) => {
    const showPageLoader = options?.showPageLoader ?? true;
    if (showPageLoader) {
      setLoading(true);
    }
    setManifestLoading(true);
    setError(null);
    setManifestError(null);
    try {
      const [detail, runList, manifestData] = await Promise.all([
        getAdapter(adapterKey),
        listScraperRuns({ adapter_key: adapterKey, limit: 5 }),
        getScraperManifest(adapterKey),
      ]);
      const item = adapterDetailToListItem(detail);
      setAdapterItem(item);
      setRuns(runList.items);
      setManifest(manifestData);
      onAdapterLoadedRef.current?.(item.display_name);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : scraperLabels.loadError;
      setError(message);
      setManifestError(message);
    } finally {
      if (showPageLoader) {
        setLoading(false);
      }
      setManifestLoading(false);
    }
  }, [adapterKey]);

  React.useEffect(() => {
    setIsEditing(false);
    setDraft(null);
    void loadDetail({ showPageLoader: true });
  }, [adapterKey, loadDetail]);

  React.useEffect(() => {
    const params = readSearchParams();
    if (params.get("tab") === "console" || params.get("run")) {
      onOpenScraperTest?.(adapterKey, params.get("run") ?? undefined);
    }
  }, [adapterKey, onOpenScraperTest]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const startEdit = React.useCallback(() => {
    if (!manifest) return;
    setDraft(manifestToFormState(manifest));
    setIsEditing(true);
    setError(null);
  }, [manifest]);

  const cancelEdit = React.useCallback(() => {
    setIsEditing(false);
    setDraft(null);
    setError(null);
  }, []);

  const refreshAdapterItem = React.useCallback(async () => {
    const detail = await getAdapter(adapterKey).catch(() => null);
    if (detail) {
      const item = adapterDetailToListItem(detail);
      setAdapterItem(item);
      onAdapterLoadedRef.current?.(item.display_name);
    }
  }, [adapterKey]);

  const refreshSavedData = React.useCallback(async () => {
    await refreshAdapterItem();
  }, [refreshAdapterItem]);

  const saveEdit = React.useCallback(async () => {
    const currentDraft = draftRef.current;
    if (!currentDraft) {
      setError(scraperLabels.manifestSaveError);
      return;
    }
    if (!currentDraft.display_name.trim()) {
      setError(scraperLabels.formAdapterName + " boş olamaz.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const savedManifest = await updateAdapterManifest(adapterKey, formStateToPayload(currentDraft));
      setManifest(savedManifest);
      await refreshSavedData();
      setIsEditing(false);
      setDraft(null);
    } catch (err) {
      setError(resolveSaveError(err));
    } finally {
      setSaving(false);
    }
  }, [adapterKey, refreshSavedData]);

  const handleDraftChange = React.useCallback(
    (updater: (current: AdapterEditFormState) => AdapterEditFormState) => {
      setDraft((current) => (current ? updater(current) : current));
    },
    [],
  );

  const openDeleteConfirm = React.useCallback(async () => {
    setDeletePreviewLoading(true);
    setError(null);
    try {
      const preview = await getAdapterDeletePreview(adapterKey);
      setDeletePreview(preview);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : scraperLabels.deleteAdapterError);
    } finally {
      setDeletePreviewLoading(false);
    }
  }, [adapterKey]);

  const closeDeleteConfirm = React.useCallback(() => {
    if (deleting) return;
    setDeletePreview(null);
  }, [deleting]);

  const handleDeleteAdapter = React.useCallback(async () => {
    setDeleting(true);
    setError(null);
    try {
      await deleteAdapter(adapterKey);
      setDeletePreview(null);
      onBack();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : scraperLabels.deleteAdapterError);
    } finally {
      setDeleting(false);
    }
  }, [adapterKey, onBack]);

  if (loading) {
    return <LoadingState />;
  }

  if (!adapterItem) {
    return (
      <div className="page adapter-detail-page">
        <div className="banner error">{error ?? scraperLabels.loadError}</div>
        <button type="button" className="btn secondary" onClick={onBack}>
          ← {scraperLabels.backToAdapters}
        </button>
      </div>
    );
  }

  const headerTitle = isEditing && draft ? draft.display_name : adapterItem.display_name;

  const headerActions: PageHeaderAction[] = isEditing
    ? [
        {
          id: "cancel",
          label: scraperLabels.formCancel,
          variant: "secondary",
          onClick: cancelEdit,
          disabled: saving,
        },
        {
          id: "save",
          label: scraperLabels.formSave,
          variant: "primary",
          onClick: () => void saveEdit(),
          loading: saving,
          disabled: saving,
        },
      ]
    : [
        {
          id: "test",
          label: scraperLabels.openInScraperTest,
          variant: "secondary",
          onClick: () => onOpenScraperTest?.(adapterKey),
          disabled: !onOpenScraperTest || isEditing || deletePreviewLoading || deleting,
        },
        {
          id: "delete",
          label: scraperLabels.deleteAdapter,
          variant: "danger",
          onClick: () => void openDeleteConfirm(),
          disabled: isEditing || deletePreviewLoading || deleting,
          loading: deletePreviewLoading,
        },
        {
          id: "edit",
          label: uiLabels.detailEdit,
          variant: "primary",
          onClick: startEdit,
          disabled: !isEditableTab || manifestLoading || !manifest || deletePreviewLoading || deleting,
        },
      ];

  return (
    <div className="page adapter-detail-page">
      <PageHeader
        title={headerTitle}
        subtitle={adapterKey}
        breadcrumbs={[{ label: scraperLabels.backToAdapters, onClick: onBack }]}
        actions={headerActions}
      />

      {error ? <div className="banner error">{error}</div> : null}

      <AdapterDetailContent
        adapterKey={adapterKey}
        runs={runs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenFair={onOpenFair}
        onViewAllRuns={onViewAllRuns}
        onOpenScraperTest={onOpenScraperTest}
        manifest={manifest}
        manifestLoading={manifestLoading}
        manifestError={manifestError}
        isEditing={isEditing}
        draft={draft}
        onDraftChange={handleDraftChange}
      />

      {deletePreview ? (
        <ConfirmDialog
          title={scraperLabels.deleteAdapterTitle}
          message={scraperLabels.buildDeleteAdapterMessage(deletePreview)}
          confirmLabel={scraperLabels.deleteAdapterConfirmLabel}
          variant="danger"
          loading={deleting}
          onCancel={closeDeleteConfirm}
          onConfirm={() => void handleDeleteAdapter()}
        />
      ) : null}
    </div>
  );
}
