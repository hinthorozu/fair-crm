import { adminLabels } from "../labels/adminLabels";
import type { EmailAccount } from "../types/smtp";

export function selectActiveEmailAccounts(accounts: EmailAccount[]): EmailAccount[] {
  return accounts.filter((account) => account.is_active);
}

export function resolveDefaultEmailAccountId(activeAccounts: EmailAccount[]): string {
  const defaultAccount = activeAccounts.find((account) => account.is_default);
  return defaultAccount?.id ?? activeAccounts[0]?.id ?? "";
}

export function formatEmailAccountOptionLabel(account: EmailAccount): string {
  if (account.is_default) {
    return `${account.name} (${adminLabels.smtpDefaultBadge})`;
  }
  return account.name;
}
