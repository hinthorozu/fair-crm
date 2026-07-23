import React from "react";
import { FieldError } from "../ui/form";
import { FormDirtyHost } from "../ui/form/FormDirty";
import { Modal } from "../ui/Modal";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { listAdapterEngines } from "../../api/scraper";
import { scraperLabels } from "../../labels/scraperLabels";
import type { AdapterEngine, CreateAdapterPayload } from "../../types/scraper";
import {
  DYNAMIC_ENGINE_VALUE,
  createEmptyFormState,
  formStateToCreatePayload,
  validateAdapterFormState,
  type AdapterFormState,
} from "../../utils/adapterManifestForm";
import {
  capabilitiesFromEngineFeatures,
  hydrateRequestedFieldsForEngineChange,
} from "../../utils/outputFieldDefinitions";
import { AdapterForm } from "./AdapterForm";

interface AdapterFormModalProps {
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: CreateAdapterPayload) => Promise<void>;
}

const FORM_ID = "adapter-create-form";

export function AdapterFormModal({ saving, error, onClose, onSubmit }: AdapterFormModalProps) {
  return (
    <FormDirtyHost onClose={onClose} confirmClassName="modal-backdrop-nested">
      <AdapterFormModalInner saving={saving} error={error} onClose={onClose} onSubmit={onSubmit} />
    </FormDirtyHost>
  );
}

function AdapterFormModalInner({ saving, error, onClose, onSubmit }: AdapterFormModalProps) {
  const emptyValues = React.useMemo(() => createEmptyFormState(), []);
  const [values, setValues] = React.useState<AdapterFormState>(emptyValues);
  const [engines, setEngines] = React.useState<AdapterEngine[]>([]);
  const [enginesLoading, setEnginesLoading] = React.useState(true);
  const [enginesError, setEnginesError] = React.useState<string | null>(null);
  const [localError, setLocalError] = React.useState<string | null>(null);

  useReportFormDirty(values, emptyValues);
  const handleCancel = useModalFormCancel(onClose);

  React.useEffect(() => {
    let cancelled = false;
    setEnginesLoading(true);
    setEnginesError(null);
    void listAdapterEngines()
      .then((response) => {
        if (cancelled) return;
        const staticEngines = response.items.filter(
          (engine) => engine.engine_type === "static" && engine.is_runnable,
        );
        setEngines(staticEngines);
        setValues((current) => {
          if (current.engine_selection !== DYNAMIC_ENGINE_VALUE || staticEngines.length === 0) {
            return current;
          }
          const engine = staticEngines[0];
          const capabilities = capabilitiesFromEngineFeatures(engine.features);
          return {
            ...createEmptyFormState(engine.engine_key, capabilities, {
              version: engine.version,
              supported_sites: engine.supported_sites,
            }),
            display_name: current.display_name,
            notes: current.notes,
          };
        });
      })
      .catch(() => {
        if (!cancelled) {
          setEnginesError(scraperLabels.formEngineLoadError);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setEnginesLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedEngine = React.useMemo(
    () => engines.find((engine) => engine.engine_key === values.engine_selection) ?? null,
    [engines, values.engine_selection],
  );

  const fieldCapabilities = React.useMemo(() => {
    if (values.engine_selection === DYNAMIC_ENGINE_VALUE) {
      return null;
    }
    if (!selectedEngine) {
      return null;
    }
    return capabilitiesFromEngineFeatures(selectedEngine.features);
  }, [selectedEngine, values.engine_selection]);

  const handleChange = React.useCallback((updater: (current: AdapterFormState) => AdapterFormState) => {
    setValues((current) => {
      const next = updater(current);
      if (next.engine_selection === current.engine_selection) {
        return next;
      }
      const engine = engines.find((item) => item.engine_key === next.engine_selection) ?? null;
      const capabilities =
        engine === null || next.engine_selection === DYNAMIC_ENGINE_VALUE
          ? null
          : capabilitiesFromEngineFeatures(engine.features);
      return {
        ...next,
        requested_fields: hydrateRequestedFieldsForEngineChange(capabilities),
        supported_sites: engine?.supported_sites?.join("\n") ?? next.supported_sites,
        version: engine?.version ?? next.version,
      };
    });
    setLocalError(null);
  }, [engines]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);

    const validationError = validateAdapterFormState(values, fieldCapabilities);
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    const payload = formStateToCreatePayload(values, fieldCapabilities);

    try {
      await onSubmit(payload);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : scraperLabels.saveError);
    }
  };

  return (
    <Modal
      title={scraperLabels.newAdapter}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <button type="button" className="btn secondary" onClick={handleCancel}>
            {scraperLabels.formCancel}
          </button>
          <button
            type="submit"
            form={FORM_ID}
            className="btn primary"
            disabled={saving || enginesLoading}
          >
            {saving ? "…" : scraperLabels.formCreate}
          </button>
        </>
      }
    >
      <form id={FORM_ID} className="adapter-form crm-form crm-form--wide" onSubmit={handleSubmit}>
        <AdapterForm
          mode="create"
          values={values}
          onChange={handleChange}
          capabilities={fieldCapabilities}
          engines={engines}
          enginesLoading={enginesLoading}
          enginesError={enginesError}
        />

        {localError || error ? <FieldError>{localError || error}</FieldError> : null}
      </form>
    </Modal>
  );
}
