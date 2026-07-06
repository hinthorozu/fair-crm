import { describe, expect, it } from "vitest";
import { parseEnrichmentResetCustomerIds } from "./enrichmentAdapter";

describe("parseEnrichmentResetCustomerIds", () => {
  const idA = "11111111-1111-1111-1111-111111111111";
  const idB = "22222222-2222-2222-2222-222222222222";

  it("parses comma-separated UUIDs", () => {
    expect(parseEnrichmentResetCustomerIds(`${idA}, ${idB}`)).toEqual([idA, idB]);
  });

  it("parses newline-separated UUIDs", () => {
    expect(parseEnrichmentResetCustomerIds(`${idA}\n${idB}`)).toEqual([idA, idB]);
  });

  it("ignores invalid tokens", () => {
    expect(parseEnrichmentResetCustomerIds(`invalid, ${idA}, not-a-uuid`)).toEqual([idA]);
  });

  it("deduplicates IDs case-insensitively", () => {
    expect(parseEnrichmentResetCustomerIds(`${idA}, ${idA.toUpperCase()}`)).toEqual([idA]);
  });

  it("returns empty array for blank input", () => {
    expect(parseEnrichmentResetCustomerIds("  \n  ")).toEqual([]);
  });
});
