import React from "react";
import { Modal } from "../ui/Modal";
import { adminLabels } from "../../labels/adminLabels";
import type { MailOperationRecord } from "../../types/mailOperations";
import { formatMailOperationLogEntry } from "../../utils/mailOperations";

interface MailOperationLogsModalProps {
  record: MailOperationRecord | null;
  onClose: () => void;
}

export function MailOperationLogsModal({ record, onClose }: MailOperationLogsModalProps) {
  if (!record) return null;

  return (
    <Modal title={adminLabels.mailOperationsLogsTitle} onClose={onClose} size="lg">
      {record.operation_logs.length === 0 ? (
        <p className="text-muted">{adminLabels.mailOperationsNoLogs}</p>
      ) : (
        <pre className="mail-operation-logs-pre">
          {record.operation_logs.map((entry) => formatMailOperationLogEntry(entry)).join("\n")}
        </pre>
      )}
    </Modal>
  );
}
