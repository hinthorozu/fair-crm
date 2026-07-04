import React from "react";
import { getAdapter, listScraperRuns } from "../api/scraper";
import { ApiError } from "../api/client";
import {
  AdapterDetailContent,
  type AdapterDetailTab,
} from "../components/scraper/AdapterDetailContent";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { scraperLabels } from "../labels/scraperLabels";
import type { AdapterListItem, ScraperRun } from "../types/scraper";
import { adapterDetailToListItem } from "../utils/scraperAdapters";
import { buildLocationSearch, navigateWithSearch, readSearchParams } from "../utils/urlState";

interface AdapterDetailPageProps {
  adapterKey: string;
  onBack: () => void;
  onOpenFair?: (fairId: string) => void;
  onAdapterLoaded?: (displayName: string) => void;
}

const VALID_TABS: AdapterDetailTab[] = ["general", "manifest", "runs", "console", "fairs"];

function tabFromUrl(): AdapterDetailTab {
  const tab = readSearchParams().get("tab");
  if (tab && VALID_TABS.includes(tab as AdapterDetailTab)) return tab as AdapterDetailTab;
  return "general";
}

export function AdapterDetailPage({
  adapterKey,
  onBack,
  onOpenFair,
  onAdapterLoaded,
}: AdapterDetailPageProps) {
  const detailPath = `/data-integration/adapters/${encodeURIComponent(adapterKey)}`;
  const [adapterItem, setAdapterItem] = React.useState<AdapterListItem | null>(null);
  const [runs, setRuns] = React.useState<ScraperRun[]>([]);
  const [activeTab, setActiveTabState] = React.useState<AdapterDetailTab>(tabFromUrl);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const setActiveTab = React.useCallback(
    (tab: AdapterDetailTab) => {
      setActiveTabState(tab);
      const params = readSearchParams();
      if (tab === "general") params.delete("tab");
      else params.set("tab", tab);
      navigateWithSearch(detailPath, buildLocationSearch(params));
    },
    [detailPath],
  );

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const [detail, runList] = await Promise.all([
          getAdapter(adapterKey),
          listScraperRuns({ limit: 200 }),
        ]);
        if (cancelled) return;
        const item = adapterDetailToListItem(detail);
        setAdapterItem(item);
        onAdapterLoaded?.(item.display_name);
        setRuns(runList.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : scraperLabels.loadError);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [adapterKey, onAdapterLoaded]);

  React.useEffect(() => {
    const onPopState = () => setActiveTabState(tabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

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

  return (
    <div className="page adapter-detail-page">
      <PageHeader
        title={adapterItem.display_name}
        subtitle={adapterKey}
        breadcrumbs={[{ label: scraperLabels.backToAdapters, onClick: onBack }]}
      />

      {error ? <div className="banner error">{error}</div> : null}

      <AdapterDetailContent
        adapterKey={adapterKey}
        adapterItem={adapterItem}
        runs={runs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenFair={onOpenFair}
      />
    </div>
  );
}
