import type { BulkEmailOperationLogLine } from "../types/bulkEmailOperation";

/** Stable identity from backend fields — no random client IDs. */
export function bulkEmailLogLineKey(line: BulkEmailOperationLogLine): string {
  return [
    line.outbox_id ?? "",
    line.email ?? "",
    line.status ?? "",
    line.at ?? "",
    line.message,
  ].join("\u0001");
}

/** Prefer outbox_id when present so status updates replace the same console row. */
export function bulkEmailLogLineIdentity(line: BulkEmailOperationLogLine): string {
  if (line.outbox_id) return `outbox:${line.outbox_id}`;
  return `line:${bulkEmailLogLineKey(line)}`;
}

/**
 * Merge a full (or incremental) log poll into existing lines without clearing the console.
 * Same outbox_id replaces the prior row when status/message/at change; new outboxes append.
 * Lines without outbox_id are keyed by the full stable field composite.
 */
export function mergeBulkEmailLogLines(
  existing: BulkEmailOperationLogLine[],
  incoming: BulkEmailOperationLogLine[],
): BulkEmailOperationLogLine[] {
  const byId = new Map<string, BulkEmailOperationLogLine>();
  for (const line of existing) {
    byId.set(bulkEmailLogLineIdentity(line), line);
  }
  for (const line of incoming) {
    const id = bulkEmailLogLineIdentity(line);
    const prev = byId.get(id);
    if (!prev || bulkEmailLogLineKey(prev) !== bulkEmailLogLineKey(line)) {
      byId.set(id, line);
    }
  }
  return Array.from(byId.values()).sort((a, b) => {
    const aAt = a.at ?? "";
    const bAt = b.at ?? "";
    const byAt = aAt.localeCompare(bAt);
    if (byAt !== 0) return byAt;
    return bulkEmailLogLineIdentity(a).localeCompare(bulkEmailLogLineIdentity(b));
  });
}
