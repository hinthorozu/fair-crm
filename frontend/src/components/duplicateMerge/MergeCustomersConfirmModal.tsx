import React from "react";
import type {
  DuplicateGroupCustomerDetail,
  DuplicateGroupMergePreview,
} from "../../types/dataOperations";
import { Modal } from "../ui/Modal";
import { useModalFormCancel } from "../../hooks/useModalForm";
import { adminLabels } from "../../labels/adminLabels";
import { MergePreviewSummaryContent } from "./MergePreviewSummaryContent";

export interface MergeCustomersConfirmModalProps {
  open: boolean;
  preview: DuplicateGroupMergePreview | null;
  groupCustomers: DuplicateGroupCustomerDetail[];
  merging: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function MergeCustomersConfirmModal({
  open,
  preview,
  groupCustomers,
  merging,
  onClose,
  onConfirm,
}: MergeCustomersConfirmModalProps) {
  const requestClose = useModalFormCancel(onClose);

  if (!open || !preview?.is_valid) {
    return null;
  }

  return (
    <Modal title={adminLabels.dataOpMergeConfirmTitle} onClose={requestClose} size="lg">
      <div className="delete-selected-modal merge-confirm-modal">
        <p className="text-danger">{adminLabels.dataOpMergeConfirmMessage}</p>
        <MergePreviewSummaryContent
          preview={preview}
          groupCustomers={groupCustomers}
          showCustomersToDelete
        />
        <div className="form-actions">
          <button type="button" className="btn secondary" onClick={requestClose} disabled={merging}>
            {adminLabels.dataOpMergeCancel}
          </button>
          <button type="button" className="btn danger" disabled={merging} onClick={onConfirm}>
            {merging ? adminLabels.dataOpMergeExecuting : adminLabels.dataOpMergeConfirmAction}
          </button>
        </div>
      </div>
    </Modal>
  );
}
