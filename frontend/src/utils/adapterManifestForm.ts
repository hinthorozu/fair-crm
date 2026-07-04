import type {
  AdapterStatus,
  ScraperManifest,
  ScraperSupports,
  UpdateAdapterManifestPayload,
} from "../types/scraper";

export interface AdapterEditFormState {
  display_name: string;
  status: AdapterStatus;
  version: string;
  last_verified: string;
  notes: string;
  supports: ScraperSupports;
  supported_sites: string;
  output_json_handoff: boolean;
  output_excel: boolean;
  browser_requires_js: boolean;
  browser_requires_playwright: boolean;
}

export const SUPPORT_KEYS: (keyof ScraperSupports)[] = [
  "list_scraping",
  "detail_scraping",
  "pagination",
  "website",
  "email",
  "phone",
  "address",
  "category",
  "description",
];

export function manifestToFormState(manifest: ScraperManifest): AdapterEditFormState {
  const normalizedStatus = manifest.status.toLowerCase();
  const status: AdapterStatus =
    normalizedStatus === "stable" ||
    normalizedStatus === "experimental" ||
    normalizedStatus === "deprecated"
      ? normalizedStatus
      : "stable";

  return {
    display_name: manifest.display_name,
    status,
    version: manifest.version,
    last_verified: manifest.last_verified ?? "",
    notes: manifest.notes ?? "",
    supports: { ...manifest.supports },
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
    status: values.status,
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
    supports: values.supports,
  };
}
