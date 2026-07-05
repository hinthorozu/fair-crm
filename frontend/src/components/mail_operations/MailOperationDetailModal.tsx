import React from "react";
import { Modal } from "../ui/Modal";
import { adminLabels } from "../../labels/adminLabels";
import type { MailOperationRecord } from "../../types/mailOperations";
import {
  formatMailOperationDateTime,
  mailOperationSourceLabel,
  mailOperationStatusLabel,
} from "../../utils/mailOperations";

interface MailOperationDetailModalProps {
  record: MailOperationRecord | null;
  onClose: () => void;
}

export function MailOperationDetailModal({ record, onClose }: MailOperationDetailModalProps) {
  if (!record) return null;

  return (
    <Modal title={adminLabels.mailOperationsDetailTitle} onClose={onClose}>
      <div className="detail-grid compact">
        <div>
          <strong>{adminLabels.mailOperationsColDate}</strong>
          <div>{formatMailOperationDateTime(record.created_at)}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColSource}</strong>
          <div>{mailOperationSourceLabel(record.source_type, record)}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColFair}</strong>
          <div>{record.fair_name ?? "—"}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColCustomer}</strong>
          <div>{record.customer_name ?? "—"}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColRecipientEmail}</strong>
          <div>{record.recipient_email}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColSmtpAccount}</strong>
          <div>{record.smtp_account_name ?? "—"}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColTemplate}</strong>
          <div>{record.template_name ?? "—"}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColSubject}</strong>
          <div>{record.subject}</div>
        </div>
        <div>
          <strong>{adminLabels.mailOperationsColStatus}</strong>
          <div>{mailOperationStatusLabel(record.status, record)}</div>
        </div>
        <div className="span-2">
          <strong>{adminLabels.mailOperationsColError}</strong>
          <div>{record.error_message ?? "—"}</div>
        </div>
      </div>
    </Modal>
  );
}
