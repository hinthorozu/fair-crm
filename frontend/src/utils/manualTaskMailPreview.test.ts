import { describe, expect, it } from "vitest";
import {
  MANUAL_MAIL_UNRESOLVED_VARIABLES_MESSAGE,
  buildManualMailCustomerVariables,
  buildManualMailPreviewSnapshot,
  escapeHtml,
  hasUnresolvedTemplateMarkers,
  isManualMailPreviewStale,
  isUnresolvedVariableRenderError,
  resolveManualMailPreviewContent,
  toPreviewHtmlDocument,
} from "./manualTaskMailPreview";
import type { MailTemplate } from "../types/mailTemplates";

const template: MailTemplate = {
  id: "tpl-1",
  organization_id: "org",
  name: "Davet",
  key: "invite",
  subject: "Merhaba {{ customer_name }}",
  body_html: "<p>Merhaba {{ customer_name }}</p>",
  body_text: "Merhaba {{ customer_name }}",
  template_type: "transactional",
  language: "tr",
  is_active: true,
  is_default: false,
  variables_schema: null,
  created_at: "",
  updated_at: "",
};

describe("resolveManualMailPreviewContent", () => {
  it("uses rendered template subject/body when user has not edited them", () => {
    expect(
      resolveManualMailPreviewContent({
        template,
        formSubject: template.subject,
        formBody: template.body_html ?? "",
        subjectTouched: false,
        bodyTouched: false,
        renderedSubject: "Merhaba Alpha Corp",
        renderedBodyHtml: "<p>Merhaba Alpha Corp</p>",
      }),
    ).toEqual({
      subject: "Merhaba Alpha Corp",
      body: "<p>Merhaba Alpha Corp</p>",
    });
  });

  it("keeps user-edited subject and body in preview", () => {
    expect(
      resolveManualMailPreviewContent({
        template,
        formSubject: "Özel konu",
        formBody: "<p>Özel gövde</p>",
        subjectTouched: true,
        bodyTouched: true,
        renderedSubject: "Merhaba Alpha Corp",
        renderedBodyHtml: "<p>Merhaba Alpha Corp</p>",
      }),
    ).toEqual({
      subject: "Özel konu",
      body: "<p>Özel gövde</p>",
    });
  });

  it("previews template-less mail from form fields", () => {
    expect(
      resolveManualMailPreviewContent({
        template: null,
        formSubject: "Konu",
        formBody: "Gövde metni",
        subjectTouched: false,
        bodyTouched: false,
      }),
    ).toEqual({ subject: "Konu", body: "Gövde metni" });
  });
});

describe("preview stale detection", () => {
  it("requires a new preview after content changes", () => {
    const snapshot = buildManualMailPreviewSnapshot({
      recipients: ["a@example.com"],
      smtpAccountId: "smtp-1",
      templateId: "tpl-1",
      subject: "Konu",
      body: "Gövde",
    });
    expect(
      isManualMailPreviewStale(snapshot, {
        ...snapshot,
        subject: "Yeni konu",
      }),
    ).toBe(true);
    expect(isManualMailPreviewStale(snapshot, snapshot)).toBe(false);
  });
});

describe("html preview helpers", () => {
  it("escapes plain text for iframe document", () => {
    const doc = toPreviewHtmlDocument("Hello <script>alert(1)</script>");
    expect(doc).toContain("Hello &lt;script&gt;alert(1)&lt;/script&gt;");
    expect(doc).not.toContain("<script>alert(1)</script>");
  });

  it("escapes standalone script tags instead of treating them as mail html", () => {
    const doc = toPreviewHtmlDocument("<script>alert(1)</script>");
    expect(doc).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  });

  it("passes through html body for sandboxed iframe", () => {
    expect(toPreviewHtmlDocument("<p>Merhaba</p>")).toBe("<p>Merhaba</p>");
  });
});

describe("unresolved variables", () => {
  it("detects leftover jinja markers", () => {
    expect(hasUnresolvedTemplateMarkers("Merhaba {{ customer_name }}")).toBe(true);
    expect(hasUnresolvedTemplateMarkers("Merhaba Alpha")).toBe(false);
  });

  it("maps render failures to unresolved-variable UX", () => {
    expect(isUnresolvedVariableRenderError("Template render failed: 'fair_name' is undefined")).toBe(
      true,
    );
    expect(MANUAL_MAIL_UNRESOLVED_VARIABLES_MESSAGE).toBe(
      "Şablonda doldurulamayan değişkenler bulunuyor.",
    );
  });
});

describe("buildManualMailCustomerVariables", () => {
  it("maps customer display name into customer_name", () => {
    expect(
      buildManualMailCustomerVariables({
        display_name: "Alpha Corp",
        legal_name: null,
        trade_name: null,
        city: "İstanbul",
        country: "TR",
        email: "a@example.com",
      }).customer_name,
    ).toBe("Alpha Corp");
  });
});
