import { getGrantedCorePermissions } from "./corePermissions";

export const SCRAPER_PERMISSION_READ = "fair_crm.scraper.read";
export const SCRAPER_PERMISSION_CREATE = "fair_crm.scraper.create";
export const SCRAPER_PERMISSION_UPDATE = "fair_crm.scraper.update";
export const SCRAPER_PERMISSION_DELETE = "fair_crm.scraper.delete";
export const SCRAPER_PERMISSION_EXECUTE = "fair_crm.scraper.execute";

// UI action names may remain run/download, but both authorization boundaries were
// consolidated by Core to the canonical execute permission.
export const SCRAPER_PERMISSION_RUN = SCRAPER_PERMISSION_EXECUTE;
export const SCRAPER_PERMISSION_DOWNLOAD = SCRAPER_PERMISSION_EXECUTE;

export function getGrantedScraperPermissions(): Set<string> {
  return getGrantedCorePermissions();
}

export function hasScraperPermission(permissionCode: string): boolean {
  return getGrantedScraperPermissions().has(permissionCode);
}
