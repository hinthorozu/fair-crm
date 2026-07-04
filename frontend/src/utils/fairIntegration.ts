export function formatAdapterOptionLabel(displayName: string, adapterKey: string): string {
  return `${displayName} (${adapterKey})`;
}

/** Matches backend normalize_source_url: http/https with host. */
export function isValidSourceUrl(value: string): boolean {
  const text = value.trim();
  if (!text) return false;
  try {
    const parsed = new URL(text);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && parsed.hostname.length > 0;
  } catch {
    return false;
  }
}

export function parseScraperConfigJson(raw: string, invalidMessage: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parsed = JSON.parse(trimmed) as unknown;
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(invalidMessage);
  }
  return parsed as Record<string, unknown>;
}

export function scraperConfigToJsonText(value: Record<string, unknown> | null | undefined): string {
  if (!value || Object.keys(value).length === 0) return "";
  return JSON.stringify(value, null, 2);
}
