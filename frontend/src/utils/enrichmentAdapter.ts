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
