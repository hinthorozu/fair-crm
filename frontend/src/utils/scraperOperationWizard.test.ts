import { describe, expect, it } from "vitest";
import { operationLabels } from "../labels/operationLabels";
import { formatScraperConfigJson, parseScraperConfigJson } from "./scraperOperationWizard";

describe("parseScraperConfigJson", () => {
  it("accepts empty as empty object", () => {
    expect(parseScraperConfigJson("")).toEqual({ ok: true, value: {} });
    expect(parseScraperConfigJson("   ")).toEqual({ ok: true, value: {} });
  });

  it("accepts a JSON object", () => {
    expect(parseScraperConfigJson('{"max_pages": 2, "use_http": true}')).toEqual({
      ok: true,
      value: { max_pages: 2, use_http: true },
    });
  });

  it("rejects arrays, primitives, and invalid JSON", () => {
    expect(parseScraperConfigJson("[1]").ok).toBe(false);
    expect(parseScraperConfigJson('"x"').ok).toBe(false);
    expect(parseScraperConfigJson("{").ok).toBe(false);
    expect(parseScraperConfigJson("{").error).toBe(operationLabels.scraperConfigInvalidJson);
  });
});

describe("formatScraperConfigJson", () => {
  it("formats empty and populated configs", () => {
    expect(formatScraperConfigJson(null)).toBe("{\n}");
    expect(formatScraperConfigJson({ max_pages: 1 })).toContain("max_pages");
  });
});
