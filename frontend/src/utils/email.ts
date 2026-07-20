/** Client-side email validation (aligned with backend email-validator rules). */

const INVALID_EMAIL_MESSAGE = "Geçerli bir e-posta adresi girin.";

/** Split a pasted/typed recipient string on comma or semicolon. Outer trim only. */
export function splitEmailInputParts(value: string): string[] {
  return value
    .replace(/,/g, ";")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
}

/**
 * Structurally validate a single email address.
 * Caller should outer-trim; internal whitespace is never accepted or stripped.
 */
export function isValidSingleEmail(email: string): boolean {
  if (!email) return false;
  if (/\s/.test(email)) return false;
  if ((email.match(/@/g) ?? []).length !== 1) return false;

  const at = email.indexOf("@");
  if (at <= 0 || at === email.length - 1) return false;

  const local = email.slice(0, at);
  const domain = email.slice(at + 1);
  if (!local || !domain) return false;

  if (local.startsWith(".") || local.endsWith(".")) return false;
  if (domain.startsWith(".") || domain.endsWith(".")) return false;
  if (!domain.includes(".")) return false;
  if (local.includes("..") || domain.includes("..")) return false;

  // Local-part: RFC 5321 atext + '.'
  if (!/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$/.test(local)) return false;

  // Domain labels: alnum/hyphen, no empty labels, TLD alphabetic ≥ 2
  const labels = domain.split(".");
  if (labels.length < 2) return false;
  for (const label of labels) {
    if (!label || label.length > 63) return false;
    if (!/^[A-Za-z0-9-]+$/.test(label)) return false;
    if (label.startsWith("-") || label.endsWith("-")) return false;
  }
  const tld = labels[labels.length - 1];
  if (tld.length < 2 || !/^[A-Za-z]{2,}$/.test(tld)) return false;

  return true;
}

/** Returns Turkish error message or null if valid. */
export function validateMultiEmailInput(value: string): string | null {
  const text = value.trim();
  if (!text) return null;

  const parts = splitEmailInputParts(text);
  for (const part of parts) {
    if (!isValidSingleEmail(part)) {
      return `Geçersiz e-posta adresi: ${part}`;
    }
  }
  return null;
}

/**
 * Validate and normalize recipient tokens for the manual-mail add field.
 * Returns added lowercase emails, or an error without accepting any invalid token.
 */
export function parseManualRecipientInput(
  value: string,
  existing: readonly string[] = [],
): { emails: string[]; error: string | null } {
  const parts = splitEmailInputParts(value);
  if (parts.length === 0) {
    return { emails: [], error: null };
  }

  const emails: string[] = [];
  const seen = new Set(existing.map((item) => item.toLowerCase()));

  for (const part of parts) {
    if (!isValidSingleEmail(part)) {
      return { emails: [], error: INVALID_EMAIL_MESSAGE };
    }
    const normalized = part.toLowerCase();
    if (seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    emails.push(normalized);
  }

  return { emails, error: null };
}

export const emailPlaceholder = "Birden fazla e-posta için ; ile ayırın";
export const invalidEmailMessage = INVALID_EMAIL_MESSAGE;
