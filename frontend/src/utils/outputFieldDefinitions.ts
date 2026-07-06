import type { RequestedOutputField, ScraperSupports } from "../types/scraper";
import { OUTPUT_FIELD_LABELS } from "../labels/scraperLabels";

/** Canonical ordered output field keys shared by engine capabilities and requested fields UI. */
export const OUTPUT_FIELD_KEYS: RequestedOutputField[] = [
  "customerName",
  "phone",
  "email",
  "address",
  "website",
  "hall",
  "stand",
  "instagram",
  "facebook",
  "linkedin",
  "youtube",
  "notes",
];

export interface ImportOutputFieldDefinition {
  outputKey: RequestedOutputField;
  canonicalKey: string;
  label: string;
  required?: boolean;
}

/** Shared field list for scraper output fields (and Excel import common fields). */
export const IMPORT_OUTPUT_FIELD_DEFINITIONS: ImportOutputFieldDefinition[] = [
  { outputKey: "customerName", canonicalKey: "company_name", label: "Firma Adı", required: true },
  { outputKey: "phone", canonicalKey: "phone", label: "Telefon" },
  { outputKey: "email", canonicalKey: "email", label: "E-posta" },
  { outputKey: "address", canonicalKey: "address", label: "Adres" },
  { outputKey: "website", canonicalKey: "website", label: "Website" },
  { outputKey: "hall", canonicalKey: "hall", label: "Salon / Hall" },
  { outputKey: "stand", canonicalKey: "stand", label: "Stand" },
  { outputKey: "instagram", canonicalKey: "instagram_url", label: "Instagram" },
  { outputKey: "facebook", canonicalKey: "facebook_url", label: "Facebook" },
  { outputKey: "linkedin", canonicalKey: "linkedin_url", label: "LinkedIn" },
  { outputKey: "youtube", canonicalKey: "youtube_url", label: "YouTube" },
  { outputKey: "notes", canonicalKey: "notes", label: "Not" },
];

/** Excel Import-only fields (broader than scraper output). */
export const EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS = [
  { canonicalKey: "contact_first_name", label: "Yetkili Adı" },
  { canonicalKey: "contact_last_name", label: "Yetkili Soyadı" },
  { canonicalKey: "contact_title", label: "Yetkili Ünvan" },
  { canonicalKey: "contact_department", label: "Yetkili Departman" },
  { canonicalKey: "contact_email", label: "Yetkili E-posta" },
  { canonicalKey: "contact_phone", label: "Yetkili Telefon" },
  { canonicalKey: "contact_mobile_phone", label: "Yetkili Cep Telefonu" },
  { canonicalKey: "contact_linkedin", label: "Yetkili LinkedIn" },
  { canonicalKey: "contact_notes", label: "Yetkili Notu" },
  { canonicalKey: "country", label: "Ülke" },
  { canonicalKey: "city", label: "Şehir" },
  { canonicalKey: "tax_number", label: "Vergi No" },
] as const;

export const OUTPUT_KEY_TO_CANONICAL: Record<RequestedOutputField, string> = Object.fromEntries(
  IMPORT_OUTPUT_FIELD_DEFINITIONS.map((field) => [field.outputKey, field.canonicalKey]),
) as Record<RequestedOutputField, string>;

export const WIZARD_MAPPING_FIELDS = [
  ...IMPORT_OUTPUT_FIELD_DEFINITIONS.map((field) => ({
    key: field.canonicalKey,
    label: field.label,
    required: field.required,
  })),
  ...EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS.map((field) => ({
    key: field.canonicalKey,
    label: field.label,
  })),
];

export const GRID_MAPPING_FIELD_OPTIONS = [
  { value: "", label: "Kullanma" },
  ...IMPORT_OUTPUT_FIELD_DEFINITIONS.map((field) => ({
    value: field.canonicalKey,
    label: field.label,
  })),
  ...EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS.map((field) => ({
    value: field.canonicalKey,
    label: field.label,
  })),
] as const;

export const DEFAULT_REQUESTED_FIELDS: RequestedOutputField[] = [...OUTPUT_FIELD_KEYS];

export function getOutputFieldLabel(key: RequestedOutputField): string {
  return OUTPUT_FIELD_LABELS[key] ?? key;
}

/** Map legacy manifest supports flags to standard output field capability booleans. */
export function engineOutputFieldCapabilities(
  supports: ScraperSupports,
): Record<RequestedOutputField, boolean> {
  return {
    customerName: supports.list_scraping,
    phone: supports.phone,
    email: supports.email,
    address: supports.address,
    website: supports.website,
    hall: supports.list_scraping,
    stand: supports.list_scraping,
    instagram: supports.detail_scraping,
    facebook: supports.detail_scraping,
    linkedin: supports.detail_scraping,
    youtube: supports.detail_scraping,
    notes: supports.description,
  };
}

/** Build capability map from adapter engine feature list (API). */
export function capabilitiesFromEngineFeatures(
  features: Array<{ key: string; enabled: boolean }>,
): Record<RequestedOutputField, boolean> {
  const byKey = Object.fromEntries(features.map((feature) => [feature.key, feature.enabled]));
  return OUTPUT_FIELD_KEYS.reduce(
    (accumulator, key) => {
      accumulator[key] = Boolean(byKey[key]);
      return accumulator;
    },
    {} as Record<RequestedOutputField, boolean>,
  );
}

export function defaultRequestedFieldsForCapabilities(
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  if (capabilities === null) {
    return [...OUTPUT_FIELD_KEYS];
  }
  return OUTPUT_FIELD_KEYS.filter((field) => capabilities[field]);
}

export function filterRequestedFieldsByCapabilities(
  fields: RequestedOutputField[],
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  if (capabilities === null) {
    return OUTPUT_FIELD_KEYS.filter((field) => fields.includes(field));
  }
  return OUTPUT_FIELD_KEYS.filter((field) => fields.includes(field) && capabilities[field]);
}

export function hydrateRequestedFieldsForEngineChange(
  capabilities: Record<RequestedOutputField, boolean> | null,
): RequestedOutputField[] {
  return defaultRequestedFieldsForCapabilities(capabilities);
}

export function toggleRequestedFieldSelection(
  current: RequestedOutputField[],
  field: RequestedOutputField,
  enabled: boolean,
): RequestedOutputField[] {
  const selected = new Set(current);
  if (enabled) {
    selected.add(field);
  } else {
    selected.delete(field);
  }
  return OUTPUT_FIELD_KEYS.filter((key) => selected.has(key));
}
