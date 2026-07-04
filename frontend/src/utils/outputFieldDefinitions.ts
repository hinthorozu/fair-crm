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

export const DEFAULT_REQUESTED_FIELDS: RequestedOutputField[] = [
  "customerName",
  "phone",
  "email",
  "address",
  "website",
  "hall",
  "stand",
];

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
