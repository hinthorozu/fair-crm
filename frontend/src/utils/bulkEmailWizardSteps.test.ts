import { describe, expect, it } from "vitest";
import { wizardStepLabels } from "../labels/operationLabels";
import { BULK_EMAIL_WIZARD_STEPS } from "./bulkEmailWizardSteps";

describe("bulkEmailWizardSteps", () => {
  it("has exactly three steps ending on summary (no separate send step)", () => {
    expect([...BULK_EMAIL_WIZARD_STEPS]).toEqual([
      "recipient_source",
      "mail_settings",
      "summary",
    ]);
    expect(BULK_EMAIL_WIZARD_STEPS).not.toContain("send");
    expect(BULK_EMAIL_WIZARD_STEPS).toHaveLength(3);
  });

  it("maps each step to a wizard label and has no send step label", () => {
    for (const step of BULK_EMAIL_WIZARD_STEPS) {
      expect(wizardStepLabels[step]).toBeTruthy();
    }
    expect(wizardStepLabels.send).toBeUndefined();
  });
});
