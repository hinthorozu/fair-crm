import React from "react";
import { getAdapterLinkedFairs } from "../../api/scraper";
import { EmptyState } from "../ui/EmptyState";
import { LoadingState, TableSkeleton } from "../ui/LoadingState";
import { Badge } from "../ui/Badge";
import { DetailWebsite } from "../ui/DetailFields";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { scraperLabels } from "../../labels/scraperLabels";
import { fairStatusLabels } from "../../labels/fairLabels";
import type { AdapterLinkedFair } from "../../types/scraper";
import type { BadgeVariant } from "../ui/Badge";

interface AdapterLinkedFairsTabProps {
  adapterKey: string;
  active: boolean;
  onOpenFair?: (fairId: string) => void;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function formatLocation(fair: AdapterLinkedFair): string {
  const city = fair.city?.trim();
  const venue = fair.venue?.trim();
  if (city && venue) return `${city} / ${venue}`;
  return city || venue || "—";
}

function fairStatusBadgeVariant(status: string | null): BadgeVariant {
  if (status === "active") return "success";
  if (status === "planned") return "info";
  if (status === "completed") return "neutral";
  if (status === "cancelled") return "danger";
  if (status === "archived") return "neutral";
  return "default";
}

function buildColumns(onOpenFair?: (fairId: string) => void): UniversalDataTableColumn<AdapterLinkedFair>[] {
  return [
    {
      key: "name",
      title: scraperLabels.linkedFairColName,
      sortable: false,
      render: (fair) => fair.name,
    },
    {
      key: "location",
      title: scraperLabels.linkedFairColLocation,
      sortable: false,
      render: (fair) => formatLocation(fair),
    },
    {
      key: "status",
      title: scraperLabels.linkedFairColStatus,
      sortable: false,
      render: (fair) =>
        fair.status ? (
          <Badge variant={fairStatusBadgeVariant(fair.status)}>
            {fairStatusLabels[fair.status] ?? fair.status}
          </Badge>
        ) : (
          "—"
        ),
    },
    {
      key: "source_url",
      title: scraperLabels.linkedFairColSourceUrl,
      sortable: false,
      render: (fair) => <DetailWebsite value={fair.source_url} />,
    },
    {
      key: "last_import_at",
      title: scraperLabels.linkedFairColLastImport,
      sortable: false,
      render: (fair) => formatDateTime(fair.last_import_at),
    },
    {
      key: "actions",
      title: scraperLabels.colActions,
      sortable: false,
      render: (fair) => (
        <button
          type="button"
          className="btn btn-sm secondary"
          disabled={!fair.id || !onOpenFair}
          onClick={() => fair.id && onOpenFair?.(fair.id)}
        >
          {scraperLabels.linkedFairOpenFair}
        </button>
      ),
    },
  ];
}

export function AdapterLinkedFairsTab({ adapterKey, active, onOpenFair }: AdapterLinkedFairsTabProps) {
  const [fairs, setFairs] = React.useState<AdapterLinkedFair[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [loaded, setLoaded] = React.useState(false);

  React.useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    void getAdapterLinkedFairs(adapterKey)
      .then((response) => {
        if (cancelled) return;
        setFairs(response.items);
        setLoaded(true);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : scraperLabels.loadError);
        setLoaded(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [adapterKey, active]);

  const columns = React.useMemo(() => buildColumns(onOpenFair), [onOpenFair]);

  if (loading && !loaded) {
    return (
      <div className="adapter-linked-fairs-tab">
        <LoadingState variant="inline" />
        <TableSkeleton rows={3} cols={6} />
      </div>
    );
  }

  if (error) {
    return <p className="text-danger">{error}</p>;
  }

  return (
    <div className="adapter-linked-fairs-tab">
      <UniversalDataTable
        items={fairs}
        columns={columns}
        rowKey={(fair) => fair.id ?? `${fair.name}-${fair.source_url ?? "unknown"}`}
        emptyState={<EmptyState title={scraperLabels.linkedFairsEmpty} />}
        className="adapter-linked-fairs-table"
      />
    </div>
  );
}
