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
import { UniversalDataTable, type UniversalDataTableColumn } from "../ui/UniversalDataTable";
import type { FairEmailOutboxItem } from "../../types/fairBulkEmail";
import { Banner } from "../ui/Banner";

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

  const outboxColumns = React.useMemo<UniversalDataTableColumn<FairEmailOutboxItem>[]>(
    () => [
      {
        key: "recipient_name",
        title: fairLabels.bulkEmailLogsColRecipient,
        sortable: false,
        allowWrap: true,
        render: (item) => item.recipient_name ?? "—",
      },
      {
        key: "company_name",
        title: fairLabels.bulkEmailLogsColCompany,
        sortable: false,
        allowWrap: true,
        render: (item) => item.company_name,
      },
      {
        key: "recipient_source",
        title: fairLabels.bulkEmailLogsColSource,
        sortable: false,
        render: (item) =>
          item.recipient_source === "contact"
            ? fairLabels.bulkEmailSourceContact
            : fairLabels.bulkEmailSourceCustomer,
      },
      {
        key: "recipient_email",
        title: fairLabels.bulkEmailLogsColEmail,
        sortable: false,
        allowWrap: true,
        render: (item) => item.recipient_email,
      },
      {
        key: "status",
        title: fairLabels.bulkEmailLogsColStatus,
        sortable: false,
        render: (item) => (
          <Badge variant={fairEmailOutboxStatusVariant(item.status)}>
            {fairEmailOutboxStatusLabel(item.status)}
          </Badge>
        ),
      },
      {
        key: "error_message",
        title: fairLabels.bulkEmailLogsColError,
        sortable: false,
        allowWrap: true,
        render: (item) => (
          <span className="error-cell">{item.error_message ?? "—"}</span>
        ),
      },
      {
        key: "attempts",
        title: fairLabels.bulkEmailLogsColAttempts,
        sortable: false,
        render: (item) => item.attempts,
      },
      {
        key: "sent_at",
        title: fairLabels.bulkEmailLogsColSentAt,
        sortable: false,
        render: (item) => formatFairEmailDateTime(item.sent_at),
      },
    ],
    [],
  );

  return (
    <Modal
      title={fairLabels.bulkEmailLogsDetailTitle}
      onClose={onClose}
      size="lg"
      footer={
        <button type="button" className="btn secondary" onClick={onClose}>
          {labels.cancel}
        </button>
      }
    >
      {loading ? <LoadingState /> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
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

          <UniversalDataTable
            items={data.items}
            columns={outboxColumns}
            rowKey={(item) => item.id}
            className="fair-bulk-email-outbox-table"
          />
        </div>
      ) : null}
    </Modal>
  );
}
