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

  if (!canView) {
    return (
      <CardSection>
        <div className="banner warning">{fairLabels.bulkEmailPermissionPreviewDeniedDebug}</div>
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
        {polling ? <div className="banner info">{fairLabels.bulkEmailLogsPolling}</div> : null}
        {error ? <div className="banner error">{error}</div> : null}
        {loading ? <LoadingState /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState title={fairLabels.bulkEmailLogsEmpty} />
        ) : null}
        {!loading && items.length > 0 ? (
          <div className="table-scroll">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>{fairLabels.bulkEmailLogsColDate}</th>
                  <th>{fairLabels.bulkEmailLogsColTemplate}</th>
                  <th>{fairLabels.bulkEmailLogsColSmtp}</th>
                  <th>{fairLabels.bulkEmailLogsColStatus}</th>
                  <th>{fairLabels.bulkEmailLogsColTotal}</th>
                  <th>{fairLabels.bulkEmailLogsColSent}</th>
                  <th>{fairLabels.bulkEmailLogsColFailed}</th>
                  <th>{fairLabels.bulkEmailLogsColQueued}</th>
                  <th>{labels.actions}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className={item.id === highlightBatchId ? "row-highlight" : undefined}>
                    <td>{formatFairEmailDateTime(item.created_at)}</td>
                    <td>{item.template_name ?? "—"}</td>
                    <td>{item.smtp_account_name ?? "—"}</td>
                    <td>
                      <Badge variant={fairEmailBatchStatusVariant(item.status)}>
                        {fairEmailBatchStatusLabel(item.status)}
                      </Badge>
                    </td>
                    <td>{item.total_recipients}</td>
                    <td>{item.sent_count}</td>
                    <td>{item.failed_count}</td>
                    <td>{item.queued_count}</td>
                    <td>
                      <button
                        type="button"
                        className="btn link"
                        onClick={() => setDetailBatchId(item.id)}
                      >
                        {fairLabels.bulkEmailLogsDetailAction}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
