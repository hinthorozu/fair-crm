import { describe, expect, it } from "vitest";
import {
  addDaysToIsoDate,
  applyEndDateInput,
  applyStartDateInput,
  buildFairSubmitPayload,
  isValidFairWebsite,
  normalizeFairWebsite,
  parseFairDateInput,
  resolveAutoEndDate,
} from "./fairForm";

describe("isValidFairWebsite", () => {
  it("accepts empty and protocol-less domains", () => {
    expect(isValidFairWebsite("")).toBe(true);
    expect(isValidFairWebsite("  ")).toBe(true);
    expect(isValidFairWebsite("abc.com")).toBe(true);
    expect(isValidFairWebsite("www.abc.com")).toBe(true);
    expect(isValidFairWebsite("http://abc.com")).toBe(true);
    expect(isValidFairWebsite("https://abc.com")).toBe(true);
    expect(isValidFairWebsite("https://www.abc.com/path")).toBe(true);
  });

  it("rejects invalid values", () => {
    expect(isValidFairWebsite("not a url")).toBe(false);
    expect(isValidFairWebsite("ftp://abc.com")).toBe(false);
  });
});

describe("normalizeFairWebsite", () => {
  it("normalizes all accepted input forms to the same host", () => {
    expect(normalizeFairWebsite("abc.com")).toBe("abc.com");
    expect(normalizeFairWebsite("www.abc.com")).toBe("abc.com");
    expect(normalizeFairWebsite("http://abc.com")).toBe("abc.com");
    expect(normalizeFairWebsite("https://abc.com")).toBe("abc.com");
    expect(normalizeFairWebsite("https://www.abc.com/about")).toBe("abc.com");
  });
});

describe("parseFairDateInput", () => {
  it("parses ISO and Turkish formats", () => {
    expect(parseFairDateInput("2026-03-15")).toBe("2026-03-15");
    expect(parseFairDateInput("15.03.2026")).toBe("2026-03-15");
    expect(parseFairDateInput("1.3.2026")).toBe("2026-03-01");
  });

  it("rejects invalid dates", () => {
    expect(parseFairDateInput("")).toBeNull();
    expect(parseFairDateInput("2026-13-01")).toBeNull();
    expect(parseFairDateInput("2026-02-30")).toBeNull();
    expect(parseFairDateInput("abc")).toBeNull();
    expect(parseFairDateInput("15/03/2026")).toBeNull();
  });
});

describe("addDaysToIsoDate / resolveAutoEndDate", () => {
  it("adds three days to start date", () => {
    expect(addDaysToIsoDate("2026-03-15", 3)).toBe("2026-03-18");
  });

  it("auto-fills end when empty and not manual", () => {
    expect(
      resolveAutoEndDate({ startDate: "2026-03-15", endDate: "", endDateManual: false }),
    ).toBe("2026-03-18");
  });

  it("preserves manual end date", () => {
    expect(
      resolveAutoEndDate({
        startDate: "2026-03-15",
        endDate: "2026-03-20",
        endDateManual: true,
      }),
    ).toBeNull();
  });

  it("updates auto end when start changes and end was auto", () => {
    expect(
      resolveAutoEndDate({
        startDate: "2026-04-01",
        endDate: "2026-03-18",
        endDateManual: false,
      }),
    ).toBe("2026-04-04");
  });
});

describe("applyStartDateInput / applyEndDateInput", () => {
  it("applies auto end on valid start without waiting for blur", () => {
    expect(
      applyStartDateInput({
        raw: "2026-03-15",
        currentEndDate: "",
        endDateManual: false,
        invalidMessage: "bad",
      }),
    ).toEqual({ start_date: "2026-03-15", end_date: "2026-03-18" });
  });

  it("keeps partial typed start text without wiping it", () => {
    expect(
      applyStartDateInput({
        raw: "2026-03",
        currentEndDate: "",
        endDateManual: false,
        invalidMessage: "bad",
      }),
    ).toEqual({ start_date: "2026-03" });
  });

  it("does not overwrite manual end when start changes", () => {
    expect(
      applyStartDateInput({
        raw: "2026-04-01",
        currentEndDate: "2026-04-10",
        endDateManual: true,
        invalidMessage: "bad",
      }),
    ).toEqual({ start_date: "2026-04-01" });
  });

  it("marks end as manual when user types a valid end date", () => {
    expect(
      applyEndDateInput({ raw: "15.03.2026", invalidMessage: "bad" }),
    ).toEqual({ end_date: "2026-03-15", endDateManual: true });
  });

  it("clears manual flag when end is emptied", () => {
    expect(applyEndDateInput({ raw: "", invalidMessage: "bad" })).toEqual({
      end_date: "",
      endDateManual: false,
    });
  });
});

describe("buildFairSubmitPayload", () => {
  it("sends null for cleared optional fields", () => {
    expect(
      buildFairSubmitPayload(
        {
          name: " Test Fair ",
          organizer: "  ",
          venue: "",
          city: "İstanbul",
          country: "Türkiye",
          start_date: "",
          end_date: "2026-03-18",
          website: "",
          status: "planned",
          description: "",
          adapter_key: "",
          source_url: "",
          scraper_config_json: "",
        },
        null,
      ),
    ).toEqual({
      name: "Test Fair",
      organizer: null,
      venue: null,
      country: "Türkiye",
      city: "İstanbul",
      start_date: null,
      end_date: "2026-03-18",
      website: null,
      description: null,
      status: "planned",
      adapter_key: null,
      source_url: null,
      scraper_config: null,
    });
  });

  it("normalizes website formats before submit", () => {
    expect(
      buildFairSubmitPayload(
        {
          name: "Fair",
          status: "planned",
          website: "https://www.abc.com/path",
          scraper_config_json: "",
        },
        null,
      ).website,
    ).toBe("abc.com");
  });

  it("defaults status to planned on create payload", () => {
    expect(
      buildFairSubmitPayload(
        {
          name: "Fair",
          scraper_config_json: "",
        },
        null,
      ).status,
    ).toBe("planned");
  });
});
