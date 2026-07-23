import { operationLabels } from "../labels/operationLabels";

export type ParsedScraperConfig =
  | { ok: true; value: Record<string, unknown> }
  | { ok: false; error: string };

/** Parse operation-level scraper_config JSON (object only). Empty → {}. */
export function parseScraperConfigJson(raw: string): ParsedScraperConfig {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: true, value: {} };
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, error: operationLabels.scraperConfigInvalidJson };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch {
    return { ok: false, error: operationLabels.scraperConfigInvalidJson };
  }
}

export function formatScraperConfigJson(config: Record<string, unknown> | null | undefined): string {
  if (!config || Object.keys(config).length === 0) {
    return "{\n}";
  }
  return JSON.stringify(config, null, 2);
}
