import { apiRequest } from "./client";
import type {
  BulkEmailContentPreview,
  FairEmailBatchDetailResponse,
  FairEmailBatchListResponse,
  PreviewBulkEmailPayload,
  RecipientOptions,
  RecipientPreviewSummary,
  SendBulkEmailPayload,
  SendBulkEmailResponse,
} from "../types/fairBulkEmail";

export function previewFairBulkEmailRecipients(
  fairId: string,
  recipientOptions: RecipientOptions,
): Promise<RecipientPreviewSummary> {
  return apiRequest<RecipientPreviewSummary>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/bulk-email/preview-recipients`,
    {
      method: "POST",
      body: JSON.stringify({ recipient_options: recipientOptions }),
    },
  );
}

export function previewFairBulkEmailContent(
  fairId: string,
  payload: PreviewBulkEmailPayload,
): Promise<BulkEmailContentPreview> {
  return apiRequest<BulkEmailContentPreview>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/bulk-email/preview`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function sendFairBulkEmail(
  fairId: string,
  payload: SendBulkEmailPayload,
): Promise<SendBulkEmailResponse> {
  return apiRequest<SendBulkEmailResponse>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/bulk-email/send`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function listFairEmailBatches(fairId: string): Promise<FairEmailBatchListResponse> {
  return apiRequest<FairEmailBatchListResponse>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/bulk-email/batches`,
  );
}

export function getFairEmailBatchDetail(
  fairId: string,
  batchId: string,
): Promise<FairEmailBatchDetailResponse> {
  return apiRequest<FairEmailBatchDetailResponse>(
    `/api/v1/fairs/${encodeURIComponent(fairId)}/bulk-email/batches/${encodeURIComponent(batchId)}`,
  );
}
