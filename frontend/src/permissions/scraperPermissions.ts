import { getGrantedCorePermissions } from "./corePermissions";

export const SCRAPER_PERMISSION_RUN = "fair_crm.scraper.run";

export const SCRAPER_PERMISSIONS_ALL = [SCRAPER_PERMISSION_RUN] as const;

export function getGrantedScraperPermissions(): Set<string> {
  return getGrantedCorePermissions();
}

export function canRunScraperActions(grantedPermissions: Set<string>): boolean {
  return grantedPermissions.has(SCRAPER_PERMISSION_RUN);
}
