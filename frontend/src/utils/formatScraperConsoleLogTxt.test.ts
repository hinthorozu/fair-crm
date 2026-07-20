import { describe, expect, it } from "vitest";
import {
  formatScraperConsoleLogBlock,
  formatScraperConsoleLogExport,
  formatScraperConsoleTime,
} from "./formatScraperConsoleLogTxt";

describe("formatScraperConsoleLogTxt", () => {
  it("formats time as HH:mm:ss", () => {
    const formatted = formatScraperConsoleTime("2026-07-20T20:03:13.000Z");
    expect(formatted).toMatch(/^\d{2}:\d{2}:\d{2}$/);
  });

  it("formats enrichment log block with step label and message lines", () => {
    const block = formatScraperConsoleLogBlock(
      {
        created_at: "2026-07-20T20:03:13.000Z",
        step: "website_fetch_started",
        message: "Sayfa isteniyor:\nhttps://example.test",
      },
      true,
    );

    expect(block).toContain("[Web sitesi taranıyor]");
    expect(block).toContain("Sayfa isteniyor:\nhttps://example.test");
    expect(block.startsWith(`${formatScraperConsoleTime("2026-07-20T20:03:13.000Z")} [`)).toBe(true);
  });

  it("joins log blocks with blank lines", () => {
    const exportText = formatScraperConsoleLogExport(
      [
        {
          created_at: "2026-07-20T20:03:13.000Z",
          step: "website_fetch_started",
          message: "Sayfa isteniyor: https://a.test",
        },
        {
          created_at: "2026-07-20T20:03:15.000Z",
          step: "website_fetch_success",
          message: "Sayfa alındı: https://a.test",
        },
      ],
      true,
    );

    expect(exportText.split("\n\n").length).toBe(2);
    expect(exportText.endsWith("\n")).toBe(true);
  });
});
