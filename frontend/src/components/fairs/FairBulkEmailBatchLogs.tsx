import React from "react";
import { listFairEmailBatches } from "../../api/fairBulkEmail";
import { ApiError } from "../../api/client";
import { fairLabels } from "../../labels/fairLabels";
import { labels } from "../../labels";
import type { FairEmailBatchListItem } from "../../types/fairBulkEmail";
import {
  fairEmailBatchStatusLabel,
  fairEmailBatchStatusVariant,
  formatFairEmailDateTime,
  isActiveBatchStatus,
} from "../../utils/fairBulkEmailLogs";
import { FairBulkEmailBatchDetailModal } from "./FairBulkEmailBatchDetailModal";
import { Badge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";
import { LoadingState } from "../ui/LoadingState";
import { SectionHeader } from "../ui/SectionHeader";
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import { TableRowActions } from "../ui/TableRowActions";
import { Banner } from "../ui/Banner";

const POLL_INTERVAL_MS = 5000;

interface FairBulkEmailBatchLogsProps {
  fairId: string;
  refreshToken?: number;
  highlightBatchId?: string | null;
  canView?: boolean;
}

export function FairBulkEmailBatchLogs({
  fairId,
  refreshToken = 0,
  highlightBatchId = null,
  canView = true,
}: FairBulkEmailBatchLogsProps) {
  const [items, setItems] = React.useState<FairEmailBatchListItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [polling, setPolling] = React.useState(false);
  const [detailBatchId, setDetailBatchId] = React.useState<string | null>(null);

  const loadBatches = React.useCallback(async () => {
    if (!canView) {
      setItems([]);
      setLoading(false);
      return;
    }
    setError(null);
    try {
      const response = await listFairEmailBatches(fairId);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.bulkEmailLogsLoadError);
    } finally {
      setLoading(false);
    }
  }, [canView, fairId]);

  React.useEffect(() => {
    setLoading(true);
    void loadBatches();
  }, [loadBatches, refreshToken]);

  React.useEffect(() => {
    if (highlightBatchId) {
      setDetailBatchId(highlightBatchId);
    }
  }, [highlightBatchId]);

  React.useEffect(() => {
    const hasActive = items.some((item) => isActiveBatchStatus(item.status));
    setPolling(hasActive);
    if (!hasActive || !canView) return undefined;

    const timer = window.setInterval(() => {
      void loadBatches();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [canView, items, loadBatches]);

  const columns = React.useMemo<UniversalDataTableColumn<FairEmailBatchListItem>[]>(
    () => [
      {
        key: "created_at",
        title: fairLabels.bulkEmailLogsColDate,
        sortable: false,
        render: (item) => formatFairEmailDateTime(item.created_at),
      },
      {
        key: "template_name",
        title: fairLabels.bulkEmailLogsColTemplate,
        sortable: false,
        allowWrap: true,
        render: (item) => item.template_name ?? "—",
      },
      {
        key: "smtp_account_name",
        title: fairLabels.bulkEmailLogsColSmtp,
        sortable: false,
        render: (item) => item.smtp_account_name ?? "—",
      },
      {
        key: "status",
        title: fairLabels.bulkEmailLogsColStatus,
        sortable: false,
        render: (item) => (
          <Badge variant={fairEmailBatchStatusVariant(item.status)}>
            {fairEmailBatchStatusLabel(item.status)}
          </Badge>
        ),
      },
      {
        key: "total_recipients",
        title: fairLabels.bulkEmailLogsColTotal,
        sortable: false,
        render: (item) => item.total_recipients,
      },
      {
        key: "sent_count",
        title: fairLabels.bulkEmailLogsColSent,
        sortable: false,
        render: (item) => item.sent_count,
      },
      {
        key: "failed_count",
        title: fairLabels.bulkEmailLogsColFailed,
        sortable: false,
        render: (item) => item.failed_count,
      },
      {
        key: "queued_count",
        title: fairLabels.bulkEmailLogsColQueued,
        sortable: false,
        render: (item) => item.queued_count,
      },
      {
        key: "actions",
        title: labels.actions,
        sortable: false,
        render: (item) => (
          <TableRowActions>
            <button
              type="button"
              className="btn link"
              onClick={() => setDetailBatchId(item.id)}
            >
              {fairLabels.bulkEmailLogsDetailAction}
            </button>
          </TableRowActions>
        ),
      },
    ],
    [],
  );

  if (!canView) {
    return (
      <CardSection>
        <Banner variant="warning">{fairLabels.bulkEmailPermissionPreviewDeniedDebug}</Banner>
      </CardSection>
    );
  }

  return (
    <>
      <CardSection>
        <SectionHeader
          title={fairLabels.bulkEmailLogsTitle}
          actions={
            <button type="button" className="btn secondary" onClick={() => void loadBatches()}>
              {labels.refresh}
            </button>
          }
        />
        {polling ? <Banner variant="info">{fairLabels.bulkEmailLogsPolling}</Banner> : null}
        {error ? <Banner variant="error">{error}</Banner> : null}
        {loading ? <LoadingState /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState title={fairLabels.bulkEmailLogsEmpty} />
        ) : null}
        {!loading && items.length > 0 ? (
          <UniversalDataTable
            items={items}
            columns={columns}
            rowKey={(item) => item.id}
            loading={loading}
            error={error}
            onRetry={() => void loadBatches()}
            className="fair-bulk-email-logs-table"
          />
        ) : null}
      </CardSection>

      {detailBatchId ? (
        <FairBulkEmailBatchDetailModal
          fairId={fairId}
          batchId={detailBatchId}
          onClose={() => setDetailBatchId(null)}
        />
      ) : null}
    </>
  );
}

function CardSection({ children }: { children: React.ReactNode }) {
  return <div className="fair-bulk-email-logs">{children}</div>;
}
