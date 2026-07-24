import { scraperLabels } from "../labels/scraperLabels";
import type { CompanyNameMatchMode } from "../types/scraper";
import type { Operation } from "../types/operation";

export type EnrichmentSourceFilterRow = {
  key: string;
  label: string;
  /** Single value or multi-line fair names. */
  values: string[];
};

function trimOptional(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function companyNameMatchLabel(match: string | null): string | null {
  if (!match) return null;
  if (match === "contains") return scraperLabels.enrichmentRunCompanyNameMatchContains;
  if (match === "starts_with") return scraperLabels.enrichmentRunCompanyNameMatchStartsWith;
  return null;
}

/** Fair IDs persisted on enrichment Operation (source_ids or type_config.fair_ids). */
export function extractEnrichmentFairIds(operation: Operation): string[] {
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
 * Builds applied enrichment source/filter rows for Operation Detail.
 * Empty / unset filters are omitted. Fair names are supplied by the caller
 * (resolved from persisted fair IDs).
 */
export function buildEnrichmentSourceFilterRows(
  operation: Operation,
  fairNames: string[],
): EnrichmentSourceFilterRow[] {
  const typeConfig = operation.type_config ?? {};
  const rows: EnrichmentSourceFilterRow[] = [];

  const resolvedNames = fairNames.map((name) => name.trim()).filter(Boolean);
  if (resolvedNames.length === 1) {
    rows.push({
      key: "fairs",
      label: scraperLabels.enrichmentRunFairFilter,
      values: resolvedNames,
    });
  } else if (resolvedNames.length > 1) {
    rows.push({
      key: "fairs",
      label: scraperLabels.enrichmentRunFairPlural,
      values: resolvedNames,
    });
  }

  const companyName = trimOptional(typeConfig.company_name);
  if (companyName) {
    rows.push({
      key: "company_name",
      label: scraperLabels.enrichmentRunCompanyName,
      values: [companyName],
    });
    const matchRaw =
      typeof typeConfig.company_name_match === "string"
        ? typeConfig.company_name_match.trim()
        : "";
    const matchLabel = companyNameMatchLabel(matchRaw || "contains");
    if (matchLabel) {
      rows.push({
        key: "company_name_match",
        label: scraperLabels.enrichmentRunCompanyNameMatch,
        values: [matchLabel],
      });
    }
  }

  const address = trimOptional(typeConfig.address_contains);
  if (address) {
    rows.push({
      key: "address_contains",
      label: scraperLabels.enrichmentRunAddress,
      values: [address],
    });
  }

  if (typeConfig.limit !== null && typeConfig.limit !== undefined && typeConfig.limit !== "") {
    const limitNum =
      typeof typeConfig.limit === "number"
        ? typeConfig.limit
        : Number(String(typeConfig.limit).trim());
    if (Number.isFinite(limitNum) && limitNum > 0) {
      rows.push({
        key: "limit",
        label: scraperLabels.enrichmentRunLimit,
        values: [String(limitNum)],
      });
    }
  }

  return rows;
}

export function enrichmentCompanyNameMatchDisplay(
  match: CompanyNameMatchMode | string | null | undefined,
): string {
  return companyNameMatchLabel(match ? String(match) : null) ?? "—";
}
