/** Bulk email operation wizard — Özet is the final step; send lives on that screen. */
export const BULK_EMAIL_WIZARD_STEPS = [
  "recipient_source",
  "mail_settings",
  "summary",
] as const;

export type BulkEmailWizardStepId = (typeof BULK_EMAIL_WIZARD_STEPS)[number];

interface BulkEmailWizardContinueState {
  navigationBusy: boolean;
  validationReady: boolean;
}

/** Keep Continue clickable while idle so click-time validation can surface field errors. */
export function isBulkEmailWizardContinueDisabled({
  navigationBusy,
}: BulkEmailWizardContinueState): boolean {
  return navigationBusy;
}
