import React from "react";
import { getFair } from "../api/fairs";
import { FairEntitySelect } from "./FairEntitySelect";
import { Modal } from "./ui/Modal";
import { useModalFormCancel } from "../hooks/useModalForm";
import { adminLabels } from "../labels/adminLabels";

export interface AssignCustomersToFairModalProps {
  open: boolean;
  selectedCount: number;
  fairId: string;
  assigning: boolean;
  onFairChange: (fairId: string) => void;
  onClose: () => void;
  onAssign: () => void;
}

export function AssignCustomersToFairModal({
  open,
  selectedCount,
  fairId,
  assigning,
  onFairChange,
  onClose,
  onAssign,
}: AssignCustomersToFairModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [fairName, setFairName] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!fairId) {
      setFairName(null);
      return;
    }
    void getFair(fairId)
      .then((fair) => setFairName(fair.name))
      .catch(() => setFairName(null));
  }, [fairId]);

  if (!open) return null;

  return (
    <Modal title={adminLabels.dataOpAssignToFairTitle} onClose={requestClose}>
      <div className="assign-fair-modal">
        <p className="text-muted">{adminLabels.dataOpAssignToFairDescription}</p>
        <div className="form-field">
          <label htmlFor="assign-fair-select">{adminLabels.dataOpAssignToFairFairLabel}</label>
          <FairEntitySelect
            id="assign-fair-select"
            value={fairId}
            onChange={onFairChange}
            disabled={assigning}
            placeholder={adminLabels.dataOpAssignToFairFairPlaceholder}
          />
        </div>
        <div className="assign-fair-modal-summary">
          <p>
            <strong>{adminLabels.dataOpAssignToFairSelectedCount}:</strong> {selectedCount}
          </p>
          <p>
            <strong>{adminLabels.dataOpAssignToFairSelectedFair}:</strong>{" "}
            {fairName ?? (fairId ? adminLabels.dataOpAssignToFairFairSelected : adminLabels.dataOpAssignToFairFairNotSelected)}
          </p>
        </div>
        <div className="form-actions">
          <button type="button" className="btn secondary" onClick={requestClose} disabled={assigning}>
            {adminLabels.cancel}
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={assigning || !fairId || selectedCount === 0}
            onClick={onAssign}
          >
            {assigning ? adminLabels.dataOpAssignToFairAssigning : adminLabels.dataOpAssignToFairConfirm}
          </button>
        </div>
      </div>
    </Modal>
  );
}
