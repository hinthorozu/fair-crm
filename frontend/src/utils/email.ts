/** Client-side multi-email validation (mirrors backend rules). */

export function isValidSingleEmail(email: string): boolean {
  if (!email || !email.includes("@")) return false;
  if (email.startsWith("@") || email.endsWith("@")) return false;
  if (email.includes("@@") || email.split("@").length !== 2) return false;
  const [local, domain] = email.split("@");
  return Boolean(local.trim()) && Boolean(domain.trim());
}

/** Returns Turkish error message or null if valid. */
export function validateMultiEmailInput(value: string): string | null {
  const text = value.trim();
  if (!text) return null;

  const parts = text.replace(/,/g, ";").split(";").map((p) => p.trim()).filter(Boolean);
  for (const part of parts) {
    if (!isValidSingleEmail(part.toLowerCase())) {
      return `Geçersiz e-posta adresi: ${part}`;
    }
  }
  return null;
}

export const emailPlaceholder = "Birden fazla e-posta için ; ile ayırın";
