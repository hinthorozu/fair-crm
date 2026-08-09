import { config } from "../config";
export const QUOTE_READ = "fair_crm.quotes.read";
export const QUOTE_CREATE = "fair_crm.quotes.create";
export const QUOTE_UPDATE = "fair_crm.quotes.update";
export function getQuotePermissions(): Set<string> {
  const all = [QUOTE_READ, QUOTE_CREATE, QUOTE_UPDATE];
  if (config.devBypassEnabled) return new Set(all);
  const raw = import.meta.env.VITE_GRANTED_PERMISSIONS as string | undefined;
  if (!raw?.trim()) return new Set(all);
  return new Set(raw.split(",").map((item) => item.trim()).filter(Boolean));
}
