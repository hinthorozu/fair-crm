import React from "react";
import { Modal } from "../Modal";

interface FormModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  size?: "default" | "lg";
  /** Sticky action footer (ADR-032 mobile bottom-sheet). */
  footer?: React.ReactNode;
}

/** Modal shell for CRM forms — wraps content in the standard form layout container. */
export function FormModal({ title, onClose, children, size = "default", footer }: FormModalProps) {
  return (
    <Modal title={title} onClose={onClose} size={size} footer={footer}>
      <div className="crm-form">{children}</div>
    </Modal>
  );
}
