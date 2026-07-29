import React from "react";
import { getFair } from "../api/fairs";
import { FairEntitySelect } from "./FairEntitySelect";
import { Modal } from "./ui/Modal";
import { FormDirtyHost } from "./ui/form/FormDirty";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { fairLabels } from "../labels/fairLabels";

export interface MoveCustomersToFairModalProps {
  open: boolean;
  sourceFairId: string;
  targetFairId: string;
  moving: boolean;
  onTargetFairChange: (fairId: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}

const EMPTY_TARGET = { targetFairId: "" };

export function MoveCustomersToFairModal(props: MoveCustomersToFairModalProps) {
  if (!props.open) return null;

  return (
    <FormDirtyHost onClose={props.onClose} confirmClassName="modal-backdrop-nested">
      <MoveCustomersToFairModalInner {...props} />
    </FormDirtyHost>
  );
}

function MoveCustomersToFairModalInner({
  sourceFairId,
  targetFairId,
  moving,
  onTargetFairChange,
  onClose,
  onConfirm,
}: MoveCustomersToFairModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [targetFairName, setTargetFairName] = React.useState<string | null>(null);

  useReportFormDirty({ targetFairId }, EMPTY_TARGET);

  React.useEffect(() => {
    if (!targetFairId) {
      setTargetFairName(null);
      return;
    }
    void getFair(targetFairId)
      .then((fair) => setTargetFairName(fair.name))
      .catch(() => setTargetFairName(null));
  }, [targetFairId]);

  const confirmation = targetFairName
    ? fairLabels.moveCustomersConfirm.replace("[Target Fair]", targetFairName)
    : fairLabels.moveCustomersConfirmHint;

  return (
    <Modal
      title={fairLabels.moveCustomersTitle}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn secondary" onClick={requestClose} disabled={moving}>
            {fairLabels.moveCustomersCancel}
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={moving || !targetFairId || targetFairId === sourceFairId}
            onClick={onConfirm}
          >
            {moving ? fairLabels.moveCustomersMoving : fairLabels.moveCustomersConfirmAction}
          </button>
        </>
      }
    >
      <div className="assign-fair-modal">
        <p className="text-muted">{fairLabels.moveCustomersDescription}</p>
        <div className="form-field">
          <label htmlFor="move-customers-target-fair">{fairLabels.moveCustomersTargetLabel}</label>
          <FairEntitySelect
            id="move-customers-target-fair"
            value={targetFairId}
            onChange={onTargetFairChange}
            disabled={moving}
            excludeFairIds={[sourceFairId]}
            placeholder={fairLabels.moveCustomersTargetPlaceholder}
          />
        </div>
        <p className="text-muted" data-testid="move-customers-confirm-text">
          {confirmation}
        </p>
      </div>
    </Modal>
  );
}
