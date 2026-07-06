import { describe, expect, it } from "vitest";
import type { ScraperManifest } from "../types/scraper";
import {
  createEmptyFormState,
  formStateToCreatePayload,
  formStateToPayload,
  manifestCapabilities,
  manifestToFormState,
  resolveRequestedFieldsForManifest,
  validateAdapterFormState,
} from "./adapterManifestForm";
import { OUTPUT_FIELD_KEYS } from "./outputFieldDefinitions";

const BASE_MANIFEST: Omit<ScraperManifest, "adapter_key" | "supports" | "requested_fields"> = {
  display_name: "Test Adapter",
  version: "1.0.0",
  supported_sites: ["example.test"],
  output: { json_handoff: true, excel: true },
  browser: { requires_js: false, requires_playwright: false },
  author: "KYROX",
  notes: "",
  scraper_version: "1.0",
  target_site_version: "unknown",
  last_verified: null,
};

const TUYAP_NEW_SUPPORTS: ScraperManifest["supports"] = {
  list_scraping: true,
  detail_scraping: true,
  pagination: true,
  website: true,
  email: true,
  phone: true,
  address: true,
  category: false,
  description: true,
};

const TUYAP_OLD_SUPPORTS: ScraperManifest["supports"] = {
  list_scraping: true,
  detail_scraping: true,
  pagination: true,
  website: true,
  email: true,
  phone: true,
  address: true,
  category: false,
  description: true,
};

function buildManifest(
  adapterKey: string,
  supports: ScraperManifest["supports"],
  requestedFields?: ScraperManifest["requested_fields"],
): ScraperManifest {
  return {
    ...BASE_MANIFEST,
    adapter_key: adapterKey,
    supports,
    requested_fields: requestedFields,
  };
}

describe("resolveRequestedFieldsForManifest", () => {
  it("uses all supported defaults for tuyap_new when requested_fields is missing", () => {
    const manifest = buildManifest("tuyap_new", TUYAP_NEW_SUPPORTS);
    expect(resolveRequestedFieldsForManifest(manifest)).toEqual(OUTPUT_FIELD_KEYS);
  });

  it("uses all supported defaults for tuyap_old when requested_fields is missing", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS);
    expect(resolveRequestedFieldsForManifest(manifest)).toEqual(OUTPUT_FIELD_KEYS);
  });

  it("keeps supported stored fields for tuyap_old", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS, [
      "customerName",
      "email",
      "instagram",
      "notes",
    ]);
    expect(resolveRequestedFieldsForManifest(manifest)).toEqual([
      "customerName",
      "email",
      "instagram",
      "notes",
    ]);
  });
});

describe("manifestToFormState", () => {
  it("hydrates tuyap_old edit draft with all supported output fields", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS);
    expect(manifestToFormState(manifest).requested_fields).toEqual(OUTPUT_FIELD_KEYS);
  });
});

describe("createEmptyFormState", () => {
  it("defaults output and browser toggles to active", () => {
    const state = createEmptyFormState("tuyap_old", Object.fromEntries(
      OUTPUT_FIELD_KEYS.map((key) => [key, true]),
    ) as Record<(typeof OUTPUT_FIELD_KEYS)[number], boolean>);
    expect(state.output_json_handoff).toBe(true);
    expect(state.output_excel).toBe(true);
    expect(state.browser_requires_js).toBe(true);
    expect(state.browser_requires_playwright).toBe(true);
    expect(state.requested_fields).toEqual(OUTPUT_FIELD_KEYS);
  });
});

describe("formStateToPayload", () => {
  it("persists supported optional fields on detail save for tuyap_old", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS);
    const draft = manifestToFormState(manifest);
    draft.requested_fields = [
      "customerName",
      "email",
      "instagram",
      "notes",
      "phone",
    ];

    const payload = formStateToPayload(draft, manifestCapabilities(manifest));

    expect(payload.requested_fields).toEqual([
      "customerName",
      "email",
      "instagram",
      "notes",
      "phone",
    ]);
  });
});

describe("formStateToCreatePayload", () => {
  it("maps unified form state to create payload with manifest overlay fields", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS);
    const state = createEmptyFormState("tuyap_old", manifestCapabilities(manifest));
    state.display_name = "Demo Adapter";

    const payload = formStateToCreatePayload(state, manifestCapabilities(manifest));

    expect(payload.name).toBe("Demo Adapter");
    expect(payload.engine_key).toBe("tuyap_old");
    expect(payload.requested_fields).toEqual(OUTPUT_FIELD_KEYS);
    expect(payload.output).toEqual({ json_handoff: true, excel: true });
    expect(payload.browser).toEqual({ requires_js: true, requires_playwright: true });
  });
});

describe("validateAdapterFormState", () => {
  it("rejects empty display name and empty requested fields consistently", () => {
    const manifest = buildManifest("tuyap_old", TUYAP_OLD_SUPPORTS);
    const state = createEmptyFormState("tuyap_old", manifestCapabilities(manifest));
    state.display_name = "";
    state.requested_fields = [];

    expect(validateAdapterFormState(state, manifestCapabilities(manifest))).not.toBeNull();
  });
});
