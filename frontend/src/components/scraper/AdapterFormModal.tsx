import React from "react";
import { Modal } from "../ui/Modal";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { scraperLabels } from "../../labels/scraperLabels";
import type { AdapterDetail, AdapterStatus, CreateAdapterPayload, UpdateAdapterPayload } from "../../types/scraper";

export interface AdapterFormValues {
  adapter_key: string;
  name: string;
  description: string;
  status: AdapterStatus;
  version: string;
  manifest_json: string;
}

const EMPTY_VALUES: AdapterFormValues = {
  adapter_key: "",
  name: "",
  description: "",
  status: "experimental",
  version: "",
  manifest_json: "",
};

function valuesFromDetail(adapter: AdapterDetail): AdapterFormValues {
  return {
    adapter_key: adapter.adapter_key,
    name: adapter.name,
    description: adapter.description ?? "",
    status: (adapter.status as AdapterStatus) ?? "experimental",
    version: adapter.version ?? "",
    manifest_json: adapter.manifest ? JSON.stringify(adapter.manifest, null, 2) : "",
  };
}

function parseManifestJson(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parsed = JSON.parse(trimmed) as unknown;
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(scraperLabels.manifestInvalidJson);
  }
  return parsed as Record<string, unknown>;
}

interface AdapterFormModalProps {
  mode: "create" | "edit";
  initialAdapter?: AdapterDetail | null;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: CreateAdapterPayload | UpdateAdapterPayload) => Promise<void>;
}

function AdapterFormModalContent({
  mode,
  initialAdapter,
  saving,
  error,
  onClose,
  onSubmit,
}: AdapterFormModalProps) {
  const [values, setValues] = React.useState<AdapterFormValues>(() =>
    initialAdapter ? valuesFromDetail(initialAdapter) : EMPTY_VALUES,
  );
  const [localError, setLocalError] = React.useState<string | null>(null);

  const baseline = React.useMemo(
    () => (initialAdapter ? valuesFromDetail(initialAdapter) : EMPTY_VALUES),
    [initialAdapter],
  );
  useReportFormDirty(values, baseline);
  const handleCancel = useModalFormCancel(onClose);

  const setField = <K extends keyof AdapterFormValues>(key: K, value: AdapterFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setLocalError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    try {
      const manifest = parseManifestJson(values.manifest_json);
      if (mode === "create") {
        await onSubmit({
          adapter_key: values.adapter_key.trim().toLowerCase(),
          name: values.name.trim(),
          description: values.description.trim() || null,
          status: values.status,
          version: values.version.trim() || null,
          manifest,
        });
        return;
      }
      await onSubmit({
        name: values.name.trim(),
        description: values.description.trim() || null,
        status: values.status,
        version: values.version.trim() || null,
        manifest,
      });
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : scraperLabels.saveError);
    }
  };

  return (
    <form className="adapter-form" onSubmit={handleSubmit}>
      {mode === "create" ? (
        <label className="form-field">
          <span>{scraperLabels.formAdapterKey}</span>
          <input
            type="text"
            value={values.adapter_key}
            onChange={(event) => setField("adapter_key", event.target.value)}
            placeholder={scraperLabels.formAdapterKeyPlaceholder}
            required
            maxLength={100}
          />
        </label>
      ) : (
        <label className="form-field">
          <span>{scraperLabels.formAdapterKey}</span>
          <input type="text" value={values.adapter_key} disabled />
        </label>
      )}

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

      <label className="form-field">
        <span>{scraperLabels.colStatus}</span>
        <select value={values.status} onChange={(event) => setField("status", event.target.value as AdapterStatus)}>
          <option value="stable">{scraperLabels.statusStable}</option>
          <option value="experimental">{scraperLabels.statusExperimental}</option>
          <option value="deprecated">{scraperLabels.statusDeprecated}</option>
        </select>
      </label>

      <label className="form-field">
        <span>{scraperLabels.colVersion}</span>
        <input
          type="text"
          value={values.version}
          onChange={(event) => setField("version", event.target.value)}
          maxLength={50}
        />
      </label>

      <label className="form-field">
        <span>{scraperLabels.formManifestJson}</span>
        <textarea
          rows={8}
          value={values.manifest_json}
          onChange={(event) => setField("manifest_json", event.target.value)}
          placeholder={scraperLabels.formManifestPlaceholder}
          spellCheck={false}
        />
      </label>

      {(localError || error) && <p className="form-error">{localError || error}</p>}

      <div className="modal-actions">
        <button type="button" className="btn secondary" onClick={handleCancel}>
          {scraperLabels.formCancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? "…" : mode === "create" ? scraperLabels.formCreate : scraperLabels.formSave}
        </button>
      </div>
    </form>
  );
}

export function AdapterFormModal(props: AdapterFormModalProps) {
  const title = props.mode === "create" ? scraperLabels.newAdapter : scraperLabels.editAdapter;
  return (
    <Modal title={title} onClose={props.onClose} size="lg">
      <AdapterFormModalContent {...props} />
    </Modal>
  );
}
