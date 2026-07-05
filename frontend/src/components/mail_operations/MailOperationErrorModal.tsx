import React from "react";
import { Modal } from "../ui/Modal";
import { adminLabels } from "../../labels/adminLabels";
import type { MailOperationRecord } from "../../types/mailOperations";

interface MailOperationErrorModalProps {
  record: MailOperationRecord | null;
  onClose: () => void;
}

export function MailOperationErrorModal({ record, onClose }: MailOperationErrorModalProps) {
  if (!record) return null;

  return (
    <Modal title={adminLabels.mailOperationsErrorTitle} onClose={onClose}>
      {record.error_message ? (
        <pre className="mail-operation-error-pre">{record.error_message}</pre>
      ) : (
        <p className="text-muted">{adminLabels.mailOperationsNoError}</p>
      )}
    </Modal>
  );
}
