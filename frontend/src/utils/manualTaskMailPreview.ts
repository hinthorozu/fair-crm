import type { Customer } from "../types/customer";
import type { MailTemplate } from "../types/mailTemplates";

export const MANUAL_MAIL_UNRESOLVED_VARIABLES_MESSAGE =
  "Şablonda doldurulamayan değişkenler bulunuyor.";

export interface ManualMailPreviewSnapshot {
  recipients: string[];
  smtpAccountId: string;
  templateId: string;
  subject: string;
  body: string;
}

export interface ManualMailPreviewPayload extends ManualMailPreviewSnapshot {
  templateName: string | null;
  smtpAccountName: string;
  htmlDocument: string;
  unresolvedVariables: boolean;
}

/** Build Jinja variables for manual task mail from the open customer card. */
export function buildManualMailCustomerVariables(
  customer: Pick<Customer, "display_name" | "legal_name" | "trade_name" | "city" | "country" | "email">,
  extras?: {
    contact_first_name?: string;
    contact_last_name?: string;
    contact_title?: string;
    fair_name?: string;
    sender_name?: string;
  },
): Record<string, string> {
  return {
    customer_name: customer.display_name || customer.trade_name || customer.legal_name || "",
    contact_first_name: extras?.contact_first_name ?? "",
    contact_last_name: extras?.contact_last_name ?? "",
    contact_title: extras?.contact_title ?? "",
    fair_name: extras?.fair_name ?? "",
    hall: "",
    stand: "",
    sender_name: extras?.sender_name ?? "KYROX",
    city: customer.city ?? "",
    country: customer.country ?? "",
    email: customer.email ?? "",
  };
}

export function looksLikeHtml(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed.startsWith("<")) return false;
  // Only treat as HTML when the document opens with common mail markup roots/blocks.
  // Lone `<script>` / accidental angle brackets in plain text stay escaped.
  return /^<(?:!doctype\s+html|html\b|head\b|body\b|div\b|p\b|table\b|span\b|br\b|h[1-6]\b|ul\b|ol\b|li\b|a\b|img\b|section\b|article\b|center\b|font\b|strong\b|em\b|b\b|i\b)/i.test(
    trimmed,
  );
}

/** Escape plain text so it can safely be shown inside a sandboxed iframe. */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Build an HTML document for sandboxed iframe preview.
 * Never inject unsanitized HTML via React dangerouslySetInnerHTML — callers must use iframe sandbox.
 */
export function toPreviewHtmlDocument(body: string): string {
  const trimmed = body.trim();
  if (!trimmed) {
    return "<!DOCTYPE html><html><body></body></html>";
  }
  if (looksLikeHtml(trimmed)) {
    return trimmed;
  }
  return (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\" /></head>" +
    `<body><pre style="white-space:pre-wrap;font-family:system-ui,sans-serif;margin:1rem;">${escapeHtml(trimmed)}</pre></body></html>`
  );
}

export function hasUnresolvedTemplateMarkers(value: string): boolean {
  return /\{\{[\s\S]*?\}\}/.test(value);
}

export function resolveManualMailPreviewContent(args: {
  template: MailTemplate | null;
  formSubject: string;
  formBody: string;
  subjectTouched: boolean;
  bodyTouched: boolean;
  renderedSubject?: string | null;
  renderedBodyHtml?: string | null;
  renderedBodyText?: string | null;
}): { subject: string; body: string } {
  const formSubject = args.formSubject.trim();
  const formBody = args.formBody.trim();

  if (!args.template) {
    return { subject: formSubject, body: formBody };
  }

  const renderedBody =
    (args.renderedBodyHtml && args.renderedBodyHtml.trim()) ||
    (args.renderedBodyText && args.renderedBodyText.trim()) ||
    "";

  return {
    subject: args.subjectTouched ? formSubject : (args.renderedSubject ?? formSubject).trim(),
    body: args.bodyTouched ? formBody : renderedBody || formBody,
  };
}

export function buildManualMailPreviewSnapshot(args: {
  recipients: string[];
  smtpAccountId: string;
  templateId: string;
  subject: string;
  body: string;
}): ManualMailPreviewSnapshot {
  return {
    recipients: [...args.recipients],
    smtpAccountId: args.smtpAccountId,
    templateId: args.templateId,
    subject: args.subject.trim(),
    body: args.body.trim(),
  };
}

export function isManualMailPreviewStale(
  snapshot: ManualMailPreviewSnapshot | null,
  current: ManualMailPreviewSnapshot,
): boolean {
  if (!snapshot) return true;
  return JSON.stringify(snapshot) !== JSON.stringify(current);
}

export function isUnresolvedVariableRenderError(message: string | null | undefined): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  return (
    normalized.includes("undefined") ||
    normalized.includes("değişken") ||
    normalized.includes("variable") ||
    normalized.includes("render")
  );
}
