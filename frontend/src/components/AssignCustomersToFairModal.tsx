import React from "react";
import { getFair } from "../api/fairs";
import { FairEntitySelect } from "./FairEntitySelect";
import { Modal } from "./ui/Modal";
import { FormDirtyHost } from "./ui/form/FormDirty";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
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

const EMPTY_FAIR = { fairId: "" };

export function AssignCustomersToFairModal(props: AssignCustomersToFairModalProps) {
  if (!props.open) return null;

  return (
    <FormDirtyHost onClose={props.onClose} confirmClassName="modal-backdrop-nested">
      <AssignCustomersToFairModalInner {...props} />
    </FormDirtyHost>
  );
}

function AssignCustomersToFairModalInner({
  selectedCount,
  fairId,
  assigning,
  onFairChange,
  onClose,
  onAssign,
}: AssignCustomersToFairModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [fairName, setFairName] = React.useState<string | null>(null);

  useReportFormDirty({ fairId }, EMPTY_FAIR);

  React.useEffect(() => {
    if (!fairId) {
      setFairName(null);
      return;
    }
    void getFair(fairId)
      .then((fair) => setFairName(fair.name))
      .catch(() => setFairName(null));
  }, [fairId]);

  return (
    <Modal
      title={adminLabels.dataOpAssignToFairTitle}
      onClose={onClose}
      footer={
        <>
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
        </>
      }
    >
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
      </div>
    </Modal>
  );
}
