import type { CreateFairPayload, FairStatus } from "../types/fair";

const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const TR_DATE_RE = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/;

export type FairFormDateField = "start_date" | "end_date";

/** Accept protocol-less domains and http(s) URLs. Empty is valid (optional field). */
export function isValidFairWebsite(value: string): boolean {
  const text = value.trim();
  if (!text) return true;
  const candidate = /^https?:\/\//i.test(text) ? text : `https://${text}`;
  try {
    const parsed = new URL(candidate);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
    const host = parsed.hostname.trim();
    if (!host) return false;
    // Require a dot for normal domains (abc.com); allow localhost for local/dev.
    return host === "localhost" || host.includes(".");
  } catch {
    return false;
  }
}

function isValidYmdParts(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1 || day > 31) return false;
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

/** Parse user date text to API ISO `YYYY-MM-DD`. Accepts ISO and `DD.MM.YYYY`. */
export function parseFairDateInput(raw: string): string | null {
  const text = raw.trim();
  if (!text) return null;

  const iso = text.match(ISO_DATE_RE);
  if (iso) {
    const year = Number(iso[1]);
    const month = Number(iso[2]);
    const day = Number(iso[3]);
    if (!isValidYmdParts(year, month, day)) return null;
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }

  const tr = text.match(TR_DATE_RE);
  if (tr) {
    const day = Number(tr[1]);
    const month = Number(tr[2]);
    const year = Number(tr[3]);
    if (!isValidYmdParts(year, month, day)) return null;
    return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  return null;
}

export function addDaysToIsoDate(isoDate: string, days: number): string | null {
  const parsed = parseFairDateInput(isoDate);
  if (!parsed) return null;
  const [year, month, day] = parsed.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** End date should follow start+3 when end is empty or still auto-managed. */
export function resolveAutoEndDate(params: {
  startDate: string;
  endDate: string;
  endDateManual: boolean;
}): string | null {
  const start = params.startDate.trim();
  if (!start) return null;
  if (params.endDateManual && params.endDate.trim()) return null;
  return addDaysToIsoDate(start, 3);
}

export interface FairFormDraft {
  name: string;
  organizer?: string | null;
  venue?: string | null;
  city?: string | null;
  country?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  website?: string | null;
  status?: FairStatus;
  description?: string | null;
  adapter_key?: string | null;
  source_url?: string | null;
  scraper_config_json: string;
}

export function buildFairSubmitPayload(
  values: FairFormDraft,
  scraperConfig: Record<string, unknown> | null,
): CreateFairPayload {
  return {
    name: values.name.trim(),
    organizer: values.organizer?.trim() || null,
    venue: values.venue?.trim() || null,
    country: values.country?.trim() || null,
    city: values.city?.trim() || null,
    start_date: values.start_date?.trim() || null,
    end_date: values.end_date?.trim() || null,
    website: values.website?.trim() || null,
    description: values.description?.trim() || null,
    status: values.status ?? "planned",
    adapter_key: values.adapter_key?.trim() || null,
    source_url: values.source_url?.trim() || null,
    scraper_config: scraperConfig,
  };
}
