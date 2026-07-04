import type {
  RequestedOutputField,
  ScraperManifest,
  UpdateAdapterManifestPayload,
} from "../types/scraper";
import {
  DEFAULT_REQUESTED_FIELDS,
  OUTPUT_FIELD_KEYS,
} from "./outputFieldDefinitions";

export type { RequestedOutputField };
export { DEFAULT_REQUESTED_FIELDS, OUTPUT_FIELD_KEYS as REQUESTED_FIELD_KEYS };

export interface AdapterEditFormState {
  display_name: string;
  version: string;
  last_verified: string;
  notes: string;
  requested_fields: RequestedOutputField[];
  supported_sites: string;
  output_json_handoff: boolean;
  output_excel: boolean;
  browser_requires_js: boolean;
  browser_requires_playwright: boolean;
}

export function manifestToFormState(manifest: ScraperManifest): AdapterEditFormState {
  const requestedFields =
    manifest.requested_fields && manifest.requested_fields.length > 0
      ? manifest.requested_fields.filter((field): field is RequestedOutputField =>
          OUTPUT_FIELD_KEYS.includes(field as RequestedOutputField),
        )
      : [...DEFAULT_REQUESTED_FIELDS];

  return {
    display_name: manifest.display_name,
    version: manifest.version,
    last_verified: manifest.last_verified ?? "",
    notes: manifest.notes ?? "",
    requested_fields: requestedFields,
    supported_sites: manifest.supported_sites.join("\n"),
    output_json_handoff: manifest.output.json_handoff,
    output_excel: manifest.output.excel,
    browser_requires_js: manifest.browser.requires_js,
    browser_requires_playwright: manifest.browser.requires_playwright,
  };
}

export function formStateToPayload(values: AdapterEditFormState): UpdateAdapterManifestPayload {
  return {
    display_name: values.display_name.trim(),
    version: values.version.trim(),
    last_verified: values.last_verified.trim() || null,
    notes: values.notes,
    supported_sites: values.supported_sites,
    output: {
      json_handoff: values.output_json_handoff,
      excel: values.output_excel,
    },
    browser: {
      requires_js: values.browser_requires_js,
      requires_playwright: values.browser_requires_playwright,
    },
    requested_fields: values.requested_fields,
  };
}
