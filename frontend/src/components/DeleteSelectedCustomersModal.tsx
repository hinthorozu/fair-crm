import React from "react";
import { Modal } from "./ui/Modal";
import { useModalFormCancel } from "../hooks/useModalForm";
import { adminLabels } from "../labels/adminLabels";

export interface DeleteSelectedCustomersModalProps {
  open: boolean;
  selectedCount: number;
  deleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function DeleteSelectedCustomersModal({
  open,
  selectedCount,
  deleting,
  onClose,
  onConfirm,
}: DeleteSelectedCustomersModalProps) {
  const requestClose = useModalFormCancel(onClose);

  if (!open) return null;

  return (
    <Modal title={adminLabels.dataOpDeleteSelectedTitle} onClose={requestClose}>
      <div className="delete-selected-modal">
        <p className="text-danger">{adminLabels.dataOpDeleteSelectedWarning}</p>
        <p className="text-muted">{adminLabels.dataOpDeleteSelectedDescription}</p>
        <p>
          <strong>{adminLabels.dataOpDeleteSelectedCountLabel}:</strong> {selectedCount}
        </p>
        <div className="form-actions">
          <button type="button" className="btn secondary" onClick={requestClose} disabled={deleting}>
            {adminLabels.cancel}
          </button>
          <button
            type="button"
            className="btn danger"
            disabled={deleting || selectedCount === 0}
            onClick={onConfirm}
          >
            {deleting ? adminLabels.dataOpDeleteSelectedDeleting : adminLabels.dataOpDeleteSelectedConfirm}
          </button>
        </div>
      </div>
    </Modal>
  );
}
