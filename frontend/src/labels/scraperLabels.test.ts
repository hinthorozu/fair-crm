import { describe, expect, it } from "vitest";

import { scraperLabels } from "../labels/scraperLabels";

describe("scraper run history delete labels", () => {
  it("keeps delete label available for active statuses", () => {
    expect(scraperLabels.runHistoryDelete).toBe("Sil");
  });

  it("shows the required stop-then-delete warning for active runs", () => {
    const message = scraperLabels.buildDeleteRunHistoryMessage({
      started_at: "2026-07-22T10:00:00.000Z",
      status: "running",
      adapter_key: "tuyap_new",
      adapter_name: "TÜYAP New",
      fair_name: "Demo Fair",
    });
    expect(message).toBe(
      "Bu görev halen çalışıyor. Silme işlemi önce çalışan görevi tamamen durduracak, ardından geçmiş kaydını silecektir. Bu işlem geri alınamaz.",
    );
  });

  it("uses the same active warning for cancel_requested and cancelling", () => {
    for (const status of ["cancel_requested", "cancelling"] as const) {
      const message = scraperLabels.buildDeleteRunHistoryMessage({
        started_at: "2026-07-22T10:00:00.000Z",
        status,
        adapter_key: "tuyap_new",
      });
      expect(message).toBe(scraperLabels.runHistoryDeleteActiveWarning);
    }
  });

  it("keeps the normal delete message for completed runs", () => {
    const message = scraperLabels.buildDeleteRunHistoryMessage({
      started_at: "2026-07-22T10:00:00.000Z",
      status: "completed",
      adapter_key: "tuyap_new",
      adapter_name: "TÜYAP New",
      fair_name: "Demo Fair",
    });
    expect(message).toContain("Bu işlem geri alınamaz.");
    expect(message).toContain("Devam etmek istiyor musunuz?");
    expect(message).not.toContain("halen çalışıyor");
  });

  it("exposes empty console copy for completed runs with no logs", () => {
    expect(scraperLabels.testNoLogsYet).toBe("Henüz log kaydı yok.");
  });
});
