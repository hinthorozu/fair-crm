import type { RequestedOutputField } from "../types/scraper";

export const CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY = "customer_contact_enrichment";

export const ENRICHMENT_OUTPUT_FIELD_KEYS: RequestedOutputField[] = [
  "email",
  "phone",
  "address",
  "instagram",
  "facebook",
  "linkedin",
  "youtube",
];

export function isCustomerContactEnrichmentAdapter(adapterKey: string): boolean {
  return adapterKey.trim().toLowerCase() === CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY;
}

export function filterEnrichmentRequestedFields(fields: RequestedOutputField[]): RequestedOutputField[] {
  return ENRICHMENT_OUTPUT_FIELD_KEYS.filter((key) => fields.includes(key));
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Parse comma/newline/space-separated customer UUIDs for enrichment state reset. */
export function parseEnrichmentResetCustomerIds(input: string): string[] {
  const seen = new Set<string>();
  const ids: string[] = [];
  for (const part of input.split(/[\s,;]+/)) {
    const trimmed = part.trim();
    if (!trimmed || !UUID_PATTERN.test(trimmed)) {
      continue;
    }
    const normalized = trimmed.toLowerCase();
    if (seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    ids.push(trimmed);
  }
  return ids;
}
