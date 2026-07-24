/**
 * Single Alıcı display value for bulk-email recipient tables (wizard + detail).
 * Contact: "{recipient_name} - {company_name}"
 * Excel: recipient_name (col1) preferred, then company_name
 * Otherwise: company_name only
 * Does not invent names — only uses existing recipient_name / company_name.
 */
export function formatBulkEmailRecipientDisplay(item: {
  source: string;
  recipient_name?: string | null;
  company_name?: string | null;
}): string {
  const company = (item.company_name ?? "").trim();
  const name = (item.recipient_name ?? "").trim();
  if (item.source === "contact") {
    if (name && company) return `${name} - ${company}`;
    return name || company || "—";
  }
  if (item.source === "excel") {
    return name || company || "—";
  }
  return company || "—";
}
