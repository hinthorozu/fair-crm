import { describe, expect, it } from "vitest";
import type { RequestedOutputField } from "../types/scraper";
import {
  DEFAULT_REQUESTED_FIELDS,
  OUTPUT_FIELD_KEYS,
  defaultRequestedFieldsForCapabilities,
  filterRequestedFieldsByCapabilities,
  hydrateRequestedFieldsForEngineChange,
} from "./outputFieldDefinitions";

const TUYAP_OLD_CAPABILITIES: Record<RequestedOutputField, boolean> = {
  customerName: true,
  phone: true,
  email: true,
  address: true,
  website: true,
  hall: true,
  stand: true,
  instagram: true,
  facebook: true,
  linkedin: true,
  youtube: true,
  notes: true,
};

describe("defaultRequestedFieldsForCapabilities", () => {
  it("returns all supported defaults for tuyap_old capabilities", () => {
    expect(defaultRequestedFieldsForCapabilities(TUYAP_OLD_CAPABILITIES)).toEqual(OUTPUT_FIELD_KEYS);
  });

  it("returns full defaults for dynamic engines without capabilities", () => {
    expect(defaultRequestedFieldsForCapabilities(null)).toEqual(DEFAULT_REQUESTED_FIELDS);
    expect(DEFAULT_REQUESTED_FIELDS).toEqual(OUTPUT_FIELD_KEYS);
  });
});

describe("hydrateRequestedFieldsForEngineChange", () => {
  it("uses all supported tuyap_old capability defaults", () => {
    const hydrated = hydrateRequestedFieldsForEngineChange(TUYAP_OLD_CAPABILITIES);
    expect(hydrated).toEqual(OUTPUT_FIELD_KEYS);
  });
});

describe("filterRequestedFieldsByCapabilities", () => {
  it("keeps supported fields in payload selection", () => {
    const filtered = filterRequestedFieldsByCapabilities(
      ["customerName", "email", "instagram", "notes"],
      TUYAP_OLD_CAPABILITIES,
    );
    expect(filtered).toEqual(["customerName", "email", "instagram", "notes"]);
  });
});
