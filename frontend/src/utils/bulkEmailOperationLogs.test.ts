import { describe, expect, it } from "vitest";
import type { BulkEmailOperationLogLine } from "../types/bulkEmailOperation";
import {
  bulkEmailLogLineKey,
  mergeBulkEmailLogLines,
} from "./bulkEmailOperationLogs";

function line(
  partial: Partial<BulkEmailOperationLogLine> &
    Pick<BulkEmailOperationLogLine, "outbox_id" | "status" | "at">,
): BulkEmailOperationLogLine {
  return {
    message: partial.message ?? `${partial.status} ${partial.outbox_id}`,
    level: partial.level ?? "info",
    email: partial.email ?? null,
    ...partial,
  };
}

describe("bulkEmailOperationLogs", () => {
  it("builds a stable key from backend fields", () => {
    const a = line({
      outbox_id: "o1",
      status: "queued",
      at: "2026-01-01T00:00:00Z",
      message: "q",
    });
    const b = line({
      outbox_id: "o1",
      status: "queued",
      at: "2026-01-01T00:00:00Z",
      message: "q",
    });
    const c = line({
      outbox_id: "o1",
      status: "sent",
      at: "2026-01-01T00:01:00Z",
      message: "s",
    });
    expect(bulkEmailLogLineKey(a)).toBe(bulkEmailLogLineKey(b));
    expect(bulkEmailLogLineKey(a)).not.toBe(bulkEmailLogLineKey(c));
  });

  it("merges polls without duplicates and updates status in place", () => {
    const existing = [
      line({ outbox_id: "o1", status: "queued", at: "2026-01-01T00:00:00Z", message: "queued" }),
      line({ outbox_id: "o2", status: "sent", at: "2026-01-01T00:00:01Z", message: "sent" }),
    ];
    const incoming = [
      line({ outbox_id: "o1", status: "sent", at: "2026-01-01T00:00:02Z", message: "sent" }),
      line({ outbox_id: "o2", status: "sent", at: "2026-01-01T00:00:01Z", message: "sent" }),
      line({ outbox_id: "o3", status: "queued", at: "2026-01-01T00:00:03Z", message: "queued" }),
    ];
    const merged = mergeBulkEmailLogLines(existing, incoming);
    expect(merged.map((l) => l.outbox_id)).toEqual(["o2", "o1", "o3"]);
    expect(merged.find((l) => l.outbox_id === "o1")?.status).toBe("sent");
    expect(merged).toHaveLength(3);
  });

  it("keeps existing lines when incoming is a subset (no wipe)", () => {
    const existing = [
      line({ outbox_id: "o1", status: "sent", at: "2026-01-01T00:00:00Z" }),
      line({ outbox_id: "o2", status: "sent", at: "2026-01-01T00:00:01Z" }),
    ];
    const merged = mergeBulkEmailLogLines(existing, [
      line({ outbox_id: "o1", status: "sent", at: "2026-01-01T00:00:00Z" }),
    ]);
    expect(merged).toHaveLength(2);
  });
});
