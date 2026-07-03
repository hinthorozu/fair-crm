import React from "react";
import type { DuplicateGroupMergePreview } from "../../types/dataOperations";
import { adminLabels } from "../../labels/adminLabels";
import { Badge } from "../ui/Badge";
import { CopyableCustomerId } from "./CopyableCustomerId";
import { MergePreviewSummaryContent } from "./MergePreviewSummaryContent";

interface MergeSummaryPanelProps {
  suggestedWinnerId: string | null;
  survivingCustomerId: string;
  survivingCustomerName: string;
  survivingParticipationCount: number;
  preview: DuplicateGroupMergePreview | null;
  previewLoading: boolean;
  previewMatchesSelection: boolean;
  previewError: string | null;
  mergeExecuting: boolean;
  mergeExecuteError: string | null;
  mergeSuccessMessage: string | null;
  onMergeExecute: () => void;
}

export function MergeSummaryPanel({
  suggestedWinnerId,
  survivingCustomerId,
  survivingCustomerName,
  survivingParticipationCount,
  preview,
  previewLoading,
  previewMatchesSelection,
  previewError,
  mergeExecuting,
  mergeExecuteError,
  mergeSuccessMessage,
  onMergeExecute,
}: MergeSummaryPanelProps) {
  const displayName = preview?.merged_customer.display_name ?? survivingCustomerName;
  const displayCustomerId = preview?.surviving_customer_id ?? survivingCustomerId;
  const participationCount =
    preview?.participation_summary.total_participation_rows ?? survivingParticipationCount;
  const previewRefreshing = previewLoading || (Boolean(preview) && !previewMatchesSelection);
  const canMerge =
    Boolean(preview?.is_valid) && !previewRefreshing && previewMatchesSelection && !mergeExecuting;

  return (
    <aside className="duplicate-group-merge-summary card" aria-label={adminLabels.dataOpMergeSummaryTitle}>
      <div className="duplicate-group-merge-summary-header">
        <h3 className="duplicate-group-merge-summary-title">{adminLabels.dataOpMergeSummaryTitle}</h3>
        <span className="duplicate-group-merge-summary-live">
          {previewRefreshing ? (
            <span className="duplicate-group-merge-summary-loading">
              <span className="spinner duplicate-group-summary-spinner" aria-hidden="true" />
              {preview ? adminLabels.dataOpMergePreviewRefreshing : adminLabels.dataOpMergePreviewLoading}
            </span>
          ) : preview ? (
            adminLabels.dataOpMergeSummaryPreview
          ) : (
            adminLabels.dataOpMergeSummaryDraft
          )}
        </span>
      </div>

      {!preview && !previewRefreshing && (
        <p className="text-muted duplicate-group-summary-prompt">{adminLabels.dataOpMergePreviewPrompt}</p>
      )}

      {previewError && (
        <div className="duplicate-group-summary-validation" role="alert">
          <p className="text-danger">{previewError}</p>
        </div>
      )}

      {mergeExecuteError && (
        <div className="duplicate-group-summary-validation" role="alert">
          <p className="text-danger">{mergeExecuteError}</p>
        </div>
      )}

      {mergeSuccessMessage && (
        <div className="banner success duplicate-group-summary-banner" role="status">
          {mergeSuccessMessage}
        </div>
      )}

      <section className="duplicate-group-summary-section">
        <p className="duplicate-group-summary-section-label">{adminLabels.dataOpSurvivingCustomer}</p>
        <div className="duplicate-group-surviving-customer">
          <div className="duplicate-group-surviving-customer-head">
            <strong>{displayName}</strong>
            {suggestedWinnerId === displayCustomerId && (
              <Badge variant="success">{adminLabels.dataOpDuplicateGroupSuggestedWinnerBadge}</Badge>
            )}
          </div>
          <CopyableCustomerId value={displayCustomerId} />
          <p className="text-muted duplicate-group-surviving-meta">
            {adminLabels.dataOpSurvivingParticipations}: {participationCount}
          </p>
        </div>
      </section>

      {preview && <MergePreviewSummaryContent preview={preview} showWarnings showSurvivingCustomer={false} />}

      {preview && preview.validation_errors.length > 0 && (
        <div className="duplicate-group-summary-validation" role="alert">
          {preview.validation_errors.map((issue, index) => (
            <p key={`${issue.code}-${index}`} className="text-danger">
              {issue.message}
            </p>
          ))}
        </div>
      )}

      {preview?.is_valid && !previewRefreshing && (
        <div className="banner success duplicate-group-summary-banner" role="status">
          {adminLabels.dataOpMergePreviewReady}
        </div>
      )}

      <button
        type="button"
        className="btn primary duplicate-group-preview-btn"
        disabled={!canMerge}
        onClick={onMergeExecute}
      >
        {mergeExecuting ? (
          <span className="duplicate-group-merge-btn-loading">
            <span className="spinner duplicate-group-summary-spinner" aria-hidden="true" />
            {adminLabels.dataOpMergeExecuting}
          </span>
        ) : (
          adminLabels.dataOpMergeCustomers
        )}
      </button>
    </aside>
  );
}
