import { describe, expect, it } from "vitest";
import { operationLabels } from "./operationLabels";

describe("operationLabels live log / capabilities", () => {
  it("exposes Canlı Log title for Operation Detail", () => {
    expect(operationLabels.liveLogTitle).toBe("Canlı Log");
  });

  it("exposes empty state when no linked scraper run", () => {
    expect(operationLabels.linkedScraperRunMissing).toBe(
      "Bu otomasyona bağlı scraper çalıştırması bulunmuyor.",
    );
  });

  it("no longer exposes Operation Detail capabilities card title", () => {
    expect("capabilitiesTitle" in operationLabels).toBe(false);
  });
});
