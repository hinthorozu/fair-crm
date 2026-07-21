import React from "react";
import { Modal } from "../Modal";

interface FormModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  size?: "default" | "lg";
  /** Sticky action footer (ADR-032 mobile bottom-sheet). */
  footer?: React.ReactNode;
  /** Constrains form content width by intent. Default: standard CRUD width. */
  formWidth?: "narrow" | "standard" | "wide" | "full";
}

/** Modal shell for CRM forms — wraps content in the standard form layout container. */
export function FormModal({
  title,
  onClose,
  children,
  size = "default",
  footer,
  formWidth = "full",
}: FormModalProps) {
  return (
    <Modal title={title} onClose={onClose} size={size} footer={footer}>
      <div className={`crm-form crm-form--${formWidth}`}>{children}</div>
    </Modal>
  );
}
