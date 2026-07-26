import type { Operation } from "../types/operation";

function trimOptional(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

/**
 * Fair IDs persisted on an Operation (source_ids when source_kind=fair,
 * else type_config.fair_ids / legacy fair_id).
 * Shared by enrichment and bulk_email detail displays.
 */
export function extractOperationFairIds(operation: Operation): string[] {
  const fromSource =
    operation.source_kind === "fair"
      ? (operation.source_ids ?? []).map((id) => String(id).trim()).filter(Boolean)
      : [];
  if (fromSource.length > 0) return [...new Set(fromSource)];

  const typeConfig = operation.type_config ?? {};
  const fromList = Array.isArray(typeConfig.fair_ids)
    ? typeConfig.fair_ids.map((id) => String(id).trim()).filter(Boolean)
    : [];
  if (fromList.length > 0) return [...new Set(fromList)];

  const legacy = trimOptional(typeConfig.fair_id);
  return legacy ? [legacy] : [];
}

/**
 * Prefer resolved fair names; fall back to legacy "Fuar (n)" when names
 * cannot be resolved but fair IDs exist.
 */
export function formatOperationFairSourceLabel(
  sourceKindLabel: string,
  resolvedFairNames: string[],
  fairIdCount: number,
): string {
  const names: string[] = [];
  const seen = new Set<string>();
  for (const raw of resolvedFairNames) {
    const name = raw.trim();
    if (!name || seen.has(name)) continue;
    seen.add(name);
    names.push(name);
  }
  if (names.length > 0) {
    return names.join(", ");
  }
  if (fairIdCount > 0) {
    return `${sourceKindLabel} (${fairIdCount})`;
  }
  return sourceKindLabel || "—";
}
