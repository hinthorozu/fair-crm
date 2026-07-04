import React from "react";
import { Modal } from "../ui/Modal";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { listAdapterEngines } from "../../api/scraper";
import { scraperLabels } from "../../labels/scraperLabels";
import type { AdapterEngine, CreateAdapterPayload, RequestedOutputField } from "../../types/scraper";
import {
  DEFAULT_REQUESTED_FIELDS,
  REQUESTED_FIELD_KEYS,
} from "../../utils/adapterManifestForm";
import {
  OutputFieldsSection,
  filterRequestedFieldsByCapabilities,
  toggleRequestedFieldSelection,
} from "./OutputFieldsSection";
import { capabilitiesFromEngineFeatures } from "../../utils/outputFieldDefinitions";

const DYNAMIC_ENGINE_VALUE = "dynamic";

interface CreateAdapterFormState {
  name: string;
  description: string;
  engineSelection: string;
  requested_fields: RequestedOutputField[];
}

const EMPTY_VALUES: CreateAdapterFormState = {
  name: "",
  description: "",
  engineSelection: DYNAMIC_ENGINE_VALUE,
  requested_fields: [...DEFAULT_REQUESTED_FIELDS],
};

interface AdapterFormModalProps {
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: CreateAdapterPayload) => Promise<void>;
}

function AdapterFormModalContent({ saving, error, onClose, onSubmit }: AdapterFormModalProps) {
  const [values, setValues] = React.useState<CreateAdapterFormState>(EMPTY_VALUES);
  const [engines, setEngines] = React.useState<AdapterEngine[]>([]);
  const [enginesLoading, setEnginesLoading] = React.useState(true);
  const [enginesError, setEnginesError] = React.useState<string | null>(null);
  const [localError, setLocalError] = React.useState<string | null>(null);

  useReportFormDirty(values, EMPTY_VALUES);
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
        setValues((current) => ({
          ...current,
          engineSelection:
            current.engineSelection === DYNAMIC_ENGINE_VALUE && staticEngines.length > 0
              ? staticEngines[0].engine_key
              : current.engineSelection,
        }));
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
    () => engines.find((engine) => engine.engine_key === values.engineSelection) ?? null,
    [engines, values.engineSelection],
  );

  const fieldCapabilities = React.useMemo(() => {
    if (values.engineSelection === DYNAMIC_ENGINE_VALUE) {
      return null;
    }
    if (!selectedEngine) {
      return null;
    }
    return capabilitiesFromEngineFeatures(selectedEngine.features);
  }, [selectedEngine, values.engineSelection]);

  const setField = <K extends keyof CreateAdapterFormState>(
    key: K,
    value: CreateAdapterFormState[K],
  ) => {
    setValues((current) => ({ ...current, [key]: value }));
    setLocalError(null);
  };

  const handleEngineChange = (engineSelection: string) => {
    setValues((current) => {
      const engine =
        engineSelection === DYNAMIC_ENGINE_VALUE
          ? null
          : engines.find((item) => item.engine_key === engineSelection) ?? null;
      const capabilities =
        engine === null ? null : capabilitiesFromEngineFeatures(engine.features);
      return {
        ...current,
        engineSelection,
        requested_fields: filterRequestedFieldsByCapabilities(current.requested_fields, capabilities),
      };
    });
    setLocalError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);

    const name = values.name.trim();
    if (!name) {
      setLocalError(scraperLabels.formAdapterNameRequired);
      return;
    }

    const requestedFields = filterRequestedFieldsByCapabilities(
      values.requested_fields.filter((field): field is RequestedOutputField =>
        REQUESTED_FIELD_KEYS.includes(field),
      ),
      fieldCapabilities,
    );
    if (requestedFields.length === 0) {
      setLocalError(scraperLabels.formRequestedFieldsRequired);
      return;
    }

    const payload: CreateAdapterPayload = {
      name,
      description: values.description.trim() || null,
      requested_fields: requestedFields,
    };
    if (values.engineSelection !== DYNAMIC_ENGINE_VALUE) {
      payload.engine_key = values.engineSelection;
    }

    try {
      await onSubmit(payload);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : scraperLabels.saveError);
    }
  };

  return (
    <form className="adapter-form" onSubmit={handleSubmit}>
      <label className="form-field">
        <span>{scraperLabels.formEngine}</span>
        <select
          className="input"
          value={values.engineSelection}
          onChange={(event) => handleEngineChange(event.target.value)}
          disabled={enginesLoading}
        >
          <option value={DYNAMIC_ENGINE_VALUE}>{scraperLabels.formEngineDynamic}</option>
          {engines.map((engine) => (
            <option key={engine.engine_key} value={engine.engine_key}>
              {engine.display_name} - {engine.engine_key}
            </option>
          ))}
        </select>
        {enginesLoading ? <p className="form-hint text-muted">{scraperLabels.formEngineLoading}</p> : null}
        {enginesError ? <p className="form-error">{enginesError}</p> : null}
        {values.engineSelection === DYNAMIC_ENGINE_VALUE ? (
          <p className="form-hint">{scraperLabels.formEngineDynamicHint}</p>
        ) : null}
      </label>

      <label className="form-field">
        <span>{scraperLabels.formAdapterName}</span>
        <input
          type="text"
          value={values.name}
          onChange={(event) => setField("name", event.target.value)}
          required
          maxLength={255}
        />
      </label>

      <label className="form-field">
        <span>{scraperLabels.formDescription}</span>
        <textarea
          rows={3}
          value={values.description}
          onChange={(event) => setField("description", event.target.value)}
          maxLength={5000}
        />
      </label>

      <div className="form-field">
        <span>{scraperLabels.manifestOutputFields}</span>
        <OutputFieldsSection
          requestedFields={values.requested_fields}
          capabilities={fieldCapabilities}
          onChange={(field, enabled) =>
            setField(
              "requested_fields",
              toggleRequestedFieldSelection(values.requested_fields, field, enabled),
            )
          }
        />
      </div>

      {(localError || error) && <p className="form-error">{localError || error}</p>}

      <div className="modal-actions">
        <button type="button" className="btn secondary" onClick={handleCancel}>
          {scraperLabels.formCancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving || enginesLoading}>
          {saving ? "…" : scraperLabels.formCreate}
        </button>
      </div>
    </form>
  );
}

export function AdapterFormModal(props: AdapterFormModalProps) {
  return (
    <Modal title={scraperLabels.newAdapter} onClose={props.onClose} size="lg">
      <AdapterFormModalContent {...props} />
    </Modal>
  );
}
