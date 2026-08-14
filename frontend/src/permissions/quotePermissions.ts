import { getGrantedCorePermissions } from "./corePermissions";

export const QUOTE_READ = "fair_crm.quotes.read";
export const QUOTE_CREATE = "fair_crm.quotes.create";
export const QUOTE_UPDATE = "fair_crm.quotes.update";

export function getQuotePermissions(): Set<string> {
  return getGrantedCorePermissions();
}
