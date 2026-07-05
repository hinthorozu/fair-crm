import React from "react";
import { Modal } from "../Modal";

interface FormModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  size?: "default" | "lg";
}

/** Modal shell for CRM forms — wraps content in the standard form layout container. */
export function FormModal({ title, onClose, children, size = "default" }: FormModalProps) {
  return (
    <Modal title={title} onClose={onClose} size={size}>
      <div className="crm-form">{children}</div>
    </Modal>
  );
}
