import React from "react";
import { adminLabels } from "../../labels/adminLabels";
import { Banner } from "../ui/Banner";
import { FormSection } from "../ui/form";

export interface ProviderAccountConfigPanelProps {
  /** Future: selected provider adapter key (mailersend, mailgun, …). */
  providerKey?: string | null;
  /** Slot for future adapter-driven credential/config fields. */
  children?: React.ReactNode;
}

/**
 * UI boundary for provider-type delivery accounts.
 * Adapter-specific fields mount here later; no fake credentials in this stage.
 */
export function ProviderAccountConfigPanel({
  providerKey: _providerKey = null,
  children,
}: ProviderAccountConfigPanelProps) {
  return (
    <FormSection title={adminLabels.smtpSectionProvider}>
      <Banner variant="info">
        <strong>{adminLabels.smtpProviderUnavailableTitle}</strong>
        <p>{adminLabels.smtpProviderUnavailableDescription}</p>
      </Banner>
      {children ? <div className="email-account-provider-config-slot">{children}</div> : null}
    </FormSection>
  );
}
