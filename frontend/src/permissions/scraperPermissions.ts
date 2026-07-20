import { config } from "../config";

export const SCRAPER_PERMISSION_RUN = "fair_crm.scraper.run";

export const SCRAPER_PERMISSIONS_ALL = [SCRAPER_PERMISSION_RUN] as const;

function parseGrantedPermissions(raw: string | undefined): Set<string> | null {
  if (!raw?.trim()) return null;
  return new Set(
    raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
}

export function getGrantedScraperPermissions(): Set<string> {
  if (config.devBypassEnabled) {
    return new Set(SCRAPER_PERMISSIONS_ALL);
  }
  const configured = parseGrantedPermissions(import.meta.env.VITE_GRANTED_PERMISSIONS);
  if (configured) {
    return configured;
  }
  return new Set(SCRAPER_PERMISSIONS_ALL);
}

export function canRunScraperActions(grantedPermissions: Set<string>): boolean {
  return grantedPermissions.has(SCRAPER_PERMISSION_RUN);
}
