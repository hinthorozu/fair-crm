import { scraperLabels } from "../../labels/scraperLabels";
import { CheckboxField } from "../ui/form";
import type { RequestedOutputField, ScraperSupports } from "../../types/scraper";
import {
  OUTPUT_FIELD_KEYS,
  defaultRequestedFieldsForCapabilities,
  engineOutputFieldCapabilities,
  filterRequestedFieldsByCapabilities,
  getOutputFieldLabel,
  hydrateRequestedFieldsForEngineChange,
  toggleRequestedFieldSelection,
} from "../../utils/outputFieldDefinitions";

export {
  defaultRequestedFieldsForCapabilities,
  filterRequestedFieldsByCapabilities,
  hydrateRequestedFieldsForEngineChange,
  toggleRequestedFieldSelection,
};

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
  const effectiveSelected = filterRequestedFieldsByCapabilities(
    requestedFields.length > 0
      ? requestedFields
      : defaultRequestedFieldsForCapabilities(capabilities),
    capabilities,
  );
  const selected = new Set(effectiveSelected);
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
              <CheckboxField
                id={`output-field-${key}`}
                label={getOutputFieldLabel(key)}
                checked={supported && selected.has(key)}
                disabled={disabled}
                onChange={(checked) => onChange?.(key, checked)}
                className="output-field-label"
              />
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
