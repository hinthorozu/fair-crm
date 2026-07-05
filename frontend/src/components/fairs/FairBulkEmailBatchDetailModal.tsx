import React from "react";
import { getFairEmailBatchDetail } from "../../api/fairBulkEmail";
import { ApiError } from "../../api/client";
import { fairLabels } from "../../labels/fairLabels";
import { labels } from "../../labels";
import type { FairEmailBatchDetailResponse } from "../../types/fairBulkEmail";
import {
  fairEmailBatchStatusLabel,
  fairEmailBatchStatusVariant,
  fairEmailOutboxStatusLabel,
  fairEmailOutboxStatusVariant,
  formatFairEmailDateTime,
} from "../../utils/fairBulkEmailLogs";
import { Badge } from "../ui/Badge";
import { LoadingState } from "../ui/LoadingState";
import { Modal } from "../ui/Modal";

interface FairBulkEmailBatchDetailModalProps {
  fairId: string;
  batchId: string;
  onClose: () => void;
}

export function FairBulkEmailBatchDetailModal({
  fairId,
  batchId,
  onClose,
}: FairBulkEmailBatchDetailModalProps) {
  const [data, setData] = React.useState<FairEmailBatchDetailResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void getFairEmailBatchDetail(fairId, batchId)
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : fairLabels.bulkEmailLogsLoadError);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fairId, batchId]);

  return (
    <Modal title={fairLabels.bulkEmailLogsDetailTitle} onClose={onClose} size="lg">
      {loading ? <LoadingState /> : null}
      {error ? <div className="banner error">{error}</div> : null}
      {data ? (
        <div className="fair-bulk-email-batch-detail">
          <div className="detail-grid compact">
            <div>
              <strong>{fairLabels.bulkEmailLogsColTemplate}</strong>
              <div>{data.batch.template_name ?? "—"}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColSmtp}</strong>
              <div>{data.batch.smtp_account_name ?? "—"}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColStatus}</strong>
              <div>
                <Badge variant={fairEmailBatchStatusVariant(data.batch.status)}>
                  {fairEmailBatchStatusLabel(data.batch.status)}
                </Badge>
              </div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailSubjectLabel}</strong>
              <div>{data.batch.subject ?? "—"}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColTotal}</strong>
              <div>{data.batch.total_recipients}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColSent}</strong>
              <div>{data.batch.sent_count}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColFailed}</strong>
              <div>{data.batch.failed_count}</div>
            </div>
            <div>
              <strong>{fairLabels.bulkEmailLogsColQueued}</strong>
              <div>{data.batch.queued_count}</div>
            </div>
          </div>

          <div className="table-scroll">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>{fairLabels.bulkEmailLogsColRecipient}</th>
                  <th>{fairLabels.bulkEmailLogsColCompany}</th>
                  <th>{fairLabels.bulkEmailLogsColSource}</th>
                  <th>{fairLabels.bulkEmailLogsColEmail}</th>
                  <th>{fairLabels.bulkEmailLogsColStatus}</th>
                  <th>{fairLabels.bulkEmailLogsColError}</th>
                  <th>{fairLabels.bulkEmailLogsColAttempts}</th>
                  <th>{fairLabels.bulkEmailLogsColSentAt}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.recipient_name ?? "—"}</td>
                    <td>{item.company_name}</td>
                    <td>
                      {item.recipient_source === "contact"
                        ? fairLabels.bulkEmailSourceContact
                        : fairLabels.bulkEmailSourceCustomer}
                    </td>
                    <td>{item.recipient_email}</td>
                    <td>
                      <Badge variant={fairEmailOutboxStatusVariant(item.status)}>
                        {fairEmailOutboxStatusLabel(item.status)}
                      </Badge>
                    </td>
                    <td className="error-cell">{item.error_message ?? "—"}</td>
                    <td>{item.attempts}</td>
                    <td>{formatFairEmailDateTime(item.sent_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={onClose}>
          {labels.cancel}
        </button>
      </div>
    </Modal>
  );
}
