import React from "react";
import { getOperationWizardMetadata, listOperationTypes } from "../../api/operations";
import { ApiError } from "../../api/client";
import { Banner } from "../ui/Banner";
import { Button } from "../ui/Button";
import { LoadingState } from "../ui/LoadingState";
import { FormField, FormModal, SelectInput } from "../ui/form";
import { FormDirtyHost } from "../ui/form/FormDirty";
import { useModalFormCancel } from "../../hooks/useModalForm";
import { operationLabels, operationTypeInfo } from "../../labels/operationLabels";
import type {
  OperationType,
  OperationTypeCatalogItem,
  OperationTypeMetadata,
  WizardMetadata,
} from "../../types/operation";
import {
  buildCatalogNameMap,
  canContinueOperationType,
  sortWizardTypes,
} from "../../utils/operationWizardTypes";

export interface NewOperationTypeModalProps {
  open: boolean;
  onClose: () => void;
  onContinue: (type: OperationType) => void;
}

export function NewOperationTypeModal(props: NewOperationTypeModalProps) {
  if (!props.open) return null;

  return (
    <FormDirtyHost onClose={props.onClose} confirmClassName="modal-backdrop-nested">
      <NewOperationTypeModalInner {...props} />
    </FormDirtyHost>
  );
}

function NewOperationTypeModalInner({
  onClose,
  onContinue,
}: NewOperationTypeModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [metadata, setMetadata] = React.useState<WizardMetadata | null>(null);
  const [catalog, setCatalog] = React.useState<OperationTypeCatalogItem[]>([]);
  const [loadingMeta, setLoadingMeta] = React.useState(true);
  const [metaError, setMetaError] = React.useState<string | null>(null);
  const [selectedType, setSelectedType] = React.useState<OperationType | "">("");

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingMeta(true);
      setMetaError(null);
      try {
        const [wizardData, typesData] = await Promise.all([
          getOperationWizardMetadata(),
          listOperationTypes({ activeOnly: true }),
        ]);
        if (!cancelled) {
          setMetadata(wizardData);
          setCatalog(typesData.items);
        }
      } catch (err) {
        if (!cancelled) {
          setMetaError(err instanceof ApiError ? err.message : operationLabels.loadError);
        }
      } finally {
        if (!cancelled) setLoadingMeta(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const nameByKey = React.useMemo(() => buildCatalogNameMap(catalog), [catalog]);

  const types = React.useMemo(
    () => sortWizardTypes(metadata?.types ?? [], catalog),
    [metadata?.types, catalog],
  );

  const metaByType = React.useMemo(() => {
    const map = new Map<string, OperationTypeMetadata>();
    for (const item of types) {
      map.set(item.type, item);
    }
    return map;
  }, [types]);

  const selectedInfo = selectedType ? operationTypeInfo[selectedType] : null;
  const selectedLabel = selectedType
    ? nameByKey.get(selectedType) ?? selectedType
    : "";
  const canContinue = canContinueOperationType(selectedType, metaByType);

  return (
    <FormModal
      title={operationLabels.wizardTitle}
      onClose={onClose}
      size="md"
      formWidth="standard"
      footer={
        <>
          <Button type="button" variant="secondary" onClick={requestClose}>
            {operationLabels.dismiss}
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={!canContinue}
            onClick={() => {
              if (!selectedType || !canContinue) return;
              onContinue(selectedType);
            }}
          >
            {operationLabels.continue}
          </Button>
        </>
      }
    >
      {loadingMeta ? <LoadingState variant="inline" /> : null}

      {!loadingMeta && metaError ? <Banner variant="error">{metaError}</Banner> : null}

      {!loadingMeta && !metaError ? (
        <>
          <FormField
            label={operationLabels.typeSelectTitle}
            htmlFor="new-operation-type"
            required
            fullWidth
          >
            <SelectInput
              id="new-operation-type"
              value={selectedType}
              onChange={(event) =>
                setSelectedType((event.target.value || "") as OperationType | "")
              }
              aria-label={operationLabels.typeSelectTitle}
            >
              <option value="">{operationLabels.typeSelectPlaceholder}</option>
              {types.map((item) => {
                const label = nameByKey.get(item.type) ?? item.type;
                return (
                  <option key={item.type} value={item.type}>
                    {label}
                  </option>
                );
              })}
            </SelectInput>
          </FormField>

          {selectedInfo ? (
            <div
              aria-live="polite"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-3)",
                marginTop: "var(--space-4)",
              }}
            >
              <p style={{ margin: 0 }}>
                <strong>{selectedLabel}</strong>
              </p>
              <p className="text-muted" style={{ margin: 0 }}>
                {selectedInfo.summary}
              </p>
              <div>
                <p style={{ margin: "0 0 var(--space-1)" }}>
                  <strong>{operationLabels.typeInfoPurpose}</strong>
                </p>
                <p className="text-muted" style={{ margin: 0 }}>
                  {selectedInfo.purpose}
                </p>
              </div>
              <div>
                <p style={{ margin: "0 0 var(--space-1)" }}>
                  <strong>{operationLabels.typeInfoHow}</strong>
                </p>
                <p className="text-muted" style={{ margin: 0 }}>
                  {selectedInfo.how}
                </p>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </FormModal>
  );
}
