import { scraperLabels } from "../labels/scraperLabels";

const ENRICHMENT_STEP_LABELS: Record<string, string> = {
  candidate_selected: scraperLabels.enrichmentLogCandidateSelected,
  website_fetch_started: scraperLabels.enrichmentLogWebsiteFetchStarted,
  website_fetch_success: scraperLabels.enrichmentLogWebsiteFetchSuccess,
  website_fetch_failed: scraperLabels.enrichmentLogWebsiteFetchFailed,
  contact_extracted: scraperLabels.enrichmentLogContactExtracted,
  email_found: scraperLabels.enrichmentLogEmailFound,
  not_found: scraperLabels.enrichmentLogNotFound,
  handoff_row_created: scraperLabels.enrichmentLogHandoffRowCreated,
  run_finished: scraperLabels.enrichmentLogRunFinished,
};

export function formatScraperLogStepLabel(step: string, enrichment = false): string {
  if (enrichment && step in ENRICHMENT_STEP_LABELS) {
    return ENRICHMENT_STEP_LABELS[step] ?? step;
  }
  if (step === "browser/open_url") return "Browser";
  return step.replace(/_/g, " ");
}
