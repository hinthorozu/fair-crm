import { scraperLabels } from "../../labels/scraperLabels";
import type { RequestedOutputField, ScraperSupports } from "../../types/scraper";
import {
  DEFAULT_REQUESTED_FIELDS,
  OUTPUT_FIELD_KEYS,
  capabilitiesFromEngineFeatures,
  engineOutputFieldCapabilities,
  getOutputFieldLabel,
  toggleRequestedFieldSelection,
} from "../../utils/outputFieldDefinitions";

export { toggleRequestedFieldSelection };

interface OutputFieldsSectionProps {
  requestedFields: RequestedOutputField[];
  /** When null (e.g. dynamic engine), all fields are selectable and support badges are hidden. */
  capabilities: Record<RequestedOutputField, boolean> | null;
  readOnly?: boolean;
  onChange?: (field: RequestedOutputField, enabled: boolean) => void;
}

export function OutputFieldsSection({
  requestedFields,
  capabilities,
  readOnly = false,
  onChange,
}: OutputFieldsSectionProps) {
  const selected = new Set(requestedFields.length > 0 ? requestedFields : DEFAULT_REQUESTED_FIELDS);
  const showSupport = capabilities !== null;

  return (
    <div>
      <p className="form-hint">{scraperLabels.manifestOutputFieldsHint}</p>
      <ul className="detail-collection-list adapter-manifest-checkboxes output-fields-list">
        {OUTPUT_FIELD_KEYS.map((key) => {
          const supported = capabilities?.[key] ?? true;
          const disabled = readOnly || !onChange || (capabilities !== null && !supported);

          return (
            <li key={key} className="output-field-row">
              <label className="output-field-label">
                <input
                  type="checkbox"
                  checked={selected.has(key)}
                  disabled={disabled}
                  onChange={(event) => onChange?.(key, event.target.checked)}
                />{" "}
                {getOutputFieldLabel(key)}
              </label>
              {showSupport ? (
                <span
                  className={
                    supported ? "output-field-support supported" : "output-field-support unsupported"
                  }
                >
                  {supported ? scraperLabels.fieldSupported : scraperLabels.fieldNotSupported}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function outputFieldCapabilitiesFromSupports(
  supports: ScraperSupports,
): Record<RequestedOutputField, boolean> {
  return engineOutputFieldCapabilities(supports);
}

export function filterRequestedFieldsByCapabilities(
  fields: RequestedOutputField[],
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  if (capabilities === null) {
    return fields;
  }
  return fields.filter((field) => capabilities[field]);
}

export function defaultRequestedFieldsForCapabilities(
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  if (capabilities === null) {
    return [...DEFAULT_REQUESTED_FIELDS];
  }
  return DEFAULT_REQUESTED_FIELDS.filter((field) => capabilities[field]);
}
