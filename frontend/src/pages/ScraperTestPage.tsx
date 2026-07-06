import React from "react";
import { getScraperManifest, listAdapters } from "../api/scraper";
import { ApiError } from "../api/client";
import { AdapterRunLogConsole } from "../components/scraper/AdapterRunLogConsole";
import { Card } from "../components/ui/Card";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { scraperLabels } from "../labels/scraperLabels";
import type { AdapterListItem } from "../types/scraper";
import { readSearchParams } from "../utils/urlState";
import { isCustomerContactEnrichmentAdapter } from "../utils/enrichmentAdapter";
import { buildEnrichmentRunDetailPath } from "../utils/enrichmentRunRouting";

interface ScraperTestPageProps {
  initialAdapterKey?: string;
  focusRunId?: string | null;
}

function readPageParams(): { adapterKey?: string; runId?: string } {
  const params = readSearchParams();
  return {
    adapterKey: params.get("adapter_key") ?? undefined,
    runId: params.get("run") ?? undefined,
  };
}

export function ScraperTestPage({ initialAdapterKey, focusRunId }: ScraperTestPageProps) {
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedAdapterKey, setSelectedAdapterKey] = React.useState(
    () => initialAdapterKey ?? readPageParams().adapterKey ?? "",
  );
  const [resolvedFocusRunId, setResolvedFocusRunId] = React.useState<string | null>(
    () => focusRunId ?? readPageParams().runId ?? null,
  );
  const [outputJson, setOutputJson] = React.useState(true);
  const [outputExcel, setOutputExcel] = React.useState(false);

  React.useEffect(() => {
    void listAdapters()
      .then((response) => {
        const items = response.items.filter(
          (adapter) => !isCustomerContactEnrichmentAdapter(adapter.adapter_key),
        );
        setAdapters(items);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : scraperLabels.loadError);
      })
      .finally(() => setLoading(false));
  }, []);

  React.useEffect(() => {
    if (!selectedAdapterKey) {
      setOutputJson(true);
      setOutputExcel(false);
      return;
    }
    void getScraperManifest(selectedAdapterKey)
      .then((manifest) => {
        setOutputJson(manifest.output.json_handoff);
        setOutputExcel(manifest.output.excel);
      })
      .catch(() => {
        setOutputJson(true);
        setOutputExcel(false);
      });
  }, [selectedAdapterKey]);

  React.useEffect(() => {
    const params = readPageParams();
    const adapterFromUrl = params.adapterKey ?? initialAdapterKey;
    const runFromUrl = params.runId ?? focusRunId ?? undefined;
    if (adapterFromUrl && isCustomerContactEnrichmentAdapter(adapterFromUrl) && runFromUrl) {
      window.location.replace(buildEnrichmentRunDetailPath(runFromUrl, adapterFromUrl));
      return;
    }
    if (adapterFromUrl && isCustomerContactEnrichmentAdapter(adapterFromUrl)) {
      setSelectedAdapterKey("");
      setResolvedFocusRunId(null);
      return;
    }
  }, [focusRunId, initialAdapterKey]);

  React.useEffect(() => {
    const onPopState = () => {
      const params = readPageParams();
      if (params.adapterKey) setSelectedAdapterKey(params.adapterKey);
      setResolvedFocusRunId(params.runId ?? null);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  const selectedAdapter = adapters.find((item) => item.adapter_key === selectedAdapterKey) ?? null;

  return (
    <div className="page scraper-test-page">
      <PageHeader title={scraperLabels.testPageTitle} subtitle={scraperLabels.testPageSubtitle} />

      {error ? <div className="banner error">{error}</div> : null}

      <Card>
        <div className="scraper-test-form">
          <label htmlFor="scraper-test-adapter">
            {scraperLabels.testAdapterLabel}
            <select
              id="scraper-test-adapter"
              className="input"
              value={selectedAdapterKey}
              onChange={(event) => {
                setSelectedAdapterKey(event.target.value);
                setResolvedFocusRunId(null);
              }}
            >
              <option value="">{scraperLabels.testAdapterPlaceholder}</option>
              {adapters.map((adapter) => (
                <option key={adapter.adapter_key} value={adapter.adapter_key}>
                  {adapter.display_name} ({adapter.adapter_key})
                </option>
              ))}
            </select>
          </label>
          {selectedAdapter ? (
            <p className="text-muted scraper-test-adapter-meta">
              {scraperLabels.testAdapterMeta(
                selectedAdapter.engine_key,
                selectedAdapter.engine_type,
              )}
            </p>
          ) : null}
        </div>

        {selectedAdapterKey ? (
          <AdapterRunLogConsole
            key={`${selectedAdapterKey}:${resolvedFocusRunId ?? "new"}`}
            adapterKey={selectedAdapterKey}
            focusRunId={resolvedFocusRunId}
            outputJson={outputJson}
            outputExcel={outputExcel}
            showOutputOptions
          />
        ) : (
          <p className="text-muted">{scraperLabels.testSelectAdapterHint}</p>
        )}
      </Card>
    </div>
  );
}
