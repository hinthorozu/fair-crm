import type {
  CreateAdapterPayload,
  RequestedOutputField,
  ScraperManifest,
  UpdateAdapterManifestPayload,
} from "../types/scraper";
import {
  OUTPUT_FIELD_KEYS,
  defaultRequestedFieldsForCapabilities,
  engineOutputFieldCapabilities,
  filterRequestedFieldsByCapabilities,
} from "./outputFieldDefinitions";
import { scraperLabels } from "../labels/scraperLabels";

export type { RequestedOutputField };
export { OUTPUT_FIELD_KEYS as REQUESTED_FIELD_KEYS };
export {
  defaultRequestedFieldsForCapabilities,
  engineOutputFieldCapabilities,
  filterRequestedFieldsByCapabilities,
} from "./outputFieldDefinitions";

export const DYNAMIC_ENGINE_VALUE = "dynamic";

/** Unified adapter form state shared by create, edit, and read-only modes. */
export interface AdapterFormState {
  engine_selection: string;
  display_name: string;
  version: string;
  last_verified: string;
  notes: string;
  supported_sites: string;
  output_json_handoff: boolean;
  output_excel: boolean;
  browser_requires_js: boolean;
  browser_requires_playwright: boolean;
  requested_fields: RequestedOutputField[];
}

/** @deprecated Use AdapterFormState */
export type AdapterEditFormState = AdapterFormState;

export interface AdapterFormMetadata {
  adapter_key?: string;
  author?: string;
  scraper_version?: string;
}

const DEFAULT_OUTPUT_TOGGLES = {
  output_json_handoff: true,
  output_excel: true,
} as const;

const DEFAULT_BROWSER_TOGGLES = {
  browser_requires_js: true,
  browser_requires_playwright: true,
} as const;

export function manifestCapabilities(
  manifest: ScraperManifest,
): Record<RequestedOutputField, boolean> {
  return engineOutputFieldCapabilities(manifest.supports);
}

export function resolveRequestedFieldsForManifest(
  manifest: ScraperManifest,
  rawFields?: RequestedOutputField[] | null,
): RequestedOutputField[] {
  const capabilities = manifestCapabilities(manifest);
  const source = rawFields ?? manifest.requested_fields;
  if (source && source.length > 0) {
    const validFields = source.filter((field): field is RequestedOutputField =>
      OUTPUT_FIELD_KEYS.includes(field as RequestedOutputField),
    );
    const filtered = filterRequestedFieldsByCapabilities(validFields, capabilities);
    if (filtered.length > 0) {
      return filtered;
    }
  }
  return defaultRequestedFieldsForCapabilities(capabilities);
}

export function createEmptyFormState(
  engineSelection: string = DYNAMIC_ENGINE_VALUE,
  capabilities: Record<RequestedOutputField, boolean> | null = null,
  template?: Pick<ScraperManifest, "version" | "supported_sites"> | null,
): AdapterFormState {
  return {
    engine_selection: engineSelection,
    display_name: "",
    version: template?.version ?? "1.0.0",
    last_verified: "",
    notes: "",
    supported_sites: template?.supported_sites?.join("\n") ?? "",
    requested_fields: defaultRequestedFieldsForCapabilities(capabilities),
    ...DEFAULT_OUTPUT_TOGGLES,
    ...DEFAULT_BROWSER_TOGGLES,
  };
}

export function manifestToFormState(manifest: ScraperManifest): AdapterFormState {
  return {
    engine_selection: manifest.adapter_key,
    display_name: manifest.display_name,
    version: manifest.version,
    last_verified: manifest.last_verified ?? "",
    notes: manifest.notes ?? "",
    requested_fields: resolveRequestedFieldsForManifest(manifest),
    supported_sites: manifest.supported_sites.join("\n"),
    output_json_handoff: manifest.output.json_handoff,
    output_excel: manifest.output.excel,
    browser_requires_js: manifest.browser.requires_js,
    browser_requires_playwright: manifest.browser.requires_playwright,
  };
}

export function sanitizeRequestedFields(
  fields: RequestedOutputField[],
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  return filterRequestedFieldsByCapabilities(
    fields.filter((field): field is RequestedOutputField =>
      OUTPUT_FIELD_KEYS.includes(field as RequestedOutputField),
    ),
    capabilities,
  );
}

export function sanitizeAdapterFormState(
  values: AdapterFormState,
  capabilities: Record<RequestedOutputField, boolean> | null,
): AdapterFormState {
  return {
    ...values,
    display_name: values.display_name.trim(),
    version: values.version.trim(),
    last_verified: values.last_verified.trim(),
    notes: values.notes,
    supported_sites: values.supported_sites,
    requested_fields: sanitizeRequestedFields(values.requested_fields, capabilities),
  };
}

export function validateAdapterFormState(
  values: AdapterFormState,
  capabilities: Record<RequestedOutputField, boolean> | null,
): string | null {
  if (!values.display_name.trim()) {
    return scraperLabels.formAdapterNameRequired;
  }
  const requestedFields = sanitizeRequestedFields(values.requested_fields, capabilities);
  if (requestedFields.length === 0) {
    return scraperLabels.formRequestedFieldsRequired;
  }
  return null;
}

export function formStateToPayload(
  values: AdapterFormState,
  capabilities: Record<RequestedOutputField, boolean> | null = null,
): UpdateAdapterManifestPayload {
  const sanitized = sanitizeAdapterFormState(values, capabilities);

  return {
    display_name: sanitized.display_name,
    version: sanitized.version,
    last_verified: sanitized.last_verified || null,
    notes: sanitized.notes,
    supported_sites: sanitized.supported_sites,
    output: {
      json_handoff: sanitized.output_json_handoff,
      excel: sanitized.output_excel,
    },
    browser: {
      requires_js: sanitized.browser_requires_js,
      requires_playwright: sanitized.browser_requires_playwright,
    },
    requested_fields: sanitized.requested_fields,
  };
}

export function formStateToCreatePayload(
  values: AdapterFormState,
  capabilities: Record<RequestedOutputField, boolean> | null = null,
): CreateAdapterPayload {
  const sanitized = sanitizeAdapterFormState(values, capabilities);
  const manifestPayload = formStateToPayload(sanitized, capabilities);

  const payload: CreateAdapterPayload = {
    name: sanitized.display_name,
    description: sanitized.notes.trim() || null,
    version: sanitized.version || null,
    last_verified: manifestPayload.last_verified,
    supported_sites: manifestPayload.supported_sites,
    output: manifestPayload.output,
    browser: manifestPayload.browser,
    requested_fields: manifestPayload.requested_fields,
  };

  if (sanitized.engine_selection !== DYNAMIC_ENGINE_VALUE) {
    payload.engine_key = sanitized.engine_selection;
  }

  return payload;
}
