import { describe, expect, it } from "vitest";
import {
  buildCreateMailTemplatePayload,
  buildUpdateMailTemplatePayload,
  EMPTY_MAIL_TEMPLATE_FORM_VALUES,
  formatMailTemplateOptionLabel,
  parseRenderVariablesJson,
  resolveSubjectAfterPreview,
  selectActiveMailTemplates,
  validateMailTemplateFormValues,
} from "./mailTemplateForm";

describe("validateMailTemplateFormValues", () => {
  it("accepts valid create values with html body", () => {
    expect(
      validateMailTemplateFormValues({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Hoş geldin",
        key: "welcome_email",
        subject: "Merhaba {{ customer_name }}",
        body_html: "<p>Merhaba</p>",
      }),
    ).toBeNull();
  });

  it("accepts body_text without body_html", () => {
    expect(
      validateMailTemplateFormValues({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Hoş geldin",
        key: "welcome_email",
        subject: "Merhaba",
        body_text: "Merhaba dünya",
      }),
    ).toBeNull();
  });

  it("rejects invalid key format", () => {
    expect(
      validateMailTemplateFormValues({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Test",
        key: "Welcome-Email",
        subject: "Konu",
        body_html: "<p>html</p>",
      }),
    ).toContain("Key küçük harf");
  });

  it("rejects when both bodies are empty", () => {
    expect(
      validateMailTemplateFormValues({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Test",
        key: "welcome_email",
        subject: "Konu",
      }),
    ).toContain("en az biri");
  });

  it("rejects invalid variables_schema JSON", () => {
    expect(
      validateMailTemplateFormValues({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Test",
        key: "welcome_email",
        subject: "Konu",
        body_html: "<p>html</p>",
        variables_schema_json: "{invalid",
      }),
    ).toContain("variables_schema");
  });
});

describe("buildCreateMailTemplatePayload", () => {
  it("builds expected create payload", () => {
    expect(
      buildCreateMailTemplatePayload({
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: " Hoş geldin ",
        key: "Welcome_Email",
        subject: " Konu ",
        body_html: " <p>html</p> ",
        body_text: "",
        template_type: "transactional",
        language: "tr",
        is_active: true,
        is_default: false,
        variables_schema_json: '{"customer_name":"string"}',
      }),
    ).toEqual({
      name: "Hoş geldin",
      key: "welcome_email",
      subject: "Konu",
      body_html: "<p>html</p>",
      body_text: null,
      template_type: "transactional",
      language: "tr",
      is_active: true,
      is_default: false,
      variables_schema: { customer_name: "string" },
    });
  });
});

describe("buildUpdateMailTemplatePayload", () => {
  it("mirrors create payload shape for full edits", () => {
    const payload = buildUpdateMailTemplatePayload({
      ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
      name: "Güncel",
      key: "updated_key",
      subject: "Yeni konu",
      body_text: "Metin",
      variables_schema_json: "",
    });

    expect(payload.name).toBe("Güncel");
    // Empty schema mirrors create payload: explicit null (API clears schema).
    expect(payload.variables_schema).toBeNull();
  });

  it("sends only changed fields when initial template is provided", () => {
    const initial = {
      id: "1",
      organization_id: "org",
      name: "Hoş geldin",
      key: "welcome_email",
      subject: "Konu",
      body_html: "<p>html</p>",
      body_text: null,
      template_type: "transactional" as const,
      language: "tr",
      is_active: true,
      is_default: false,
      variables_schema: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const payload = buildUpdateMailTemplatePayload(
      {
        ...EMPTY_MAIL_TEMPLATE_FORM_VALUES,
        name: "Hoş geldin",
        key: "welcome_email",
        subject: "Konu",
        body_html: "<p>html</p>",
        is_default: true,
      },
      initial,
    );

    expect(payload).toEqual({ is_default: true });
  });
});

describe("parseRenderVariablesJson", () => {
  it("returns empty object for blank input", () => {
    expect(parseRenderVariablesJson("   ")).toEqual({});
  });

  it("parses sample variables object", () => {
    expect(parseRenderVariablesJson('{"customer_name":"ABC"}')).toEqual({
      customer_name: "ABC",
    });
  });

  it("rejects non-object JSON", () => {
    expect(() => parseRenderVariablesJson("[1,2,3]")).toThrow("JSON nesnesi");
  });
});

describe("resolveSubjectAfterPreview", () => {
  it("uses rendered subject when the user has not edited the field", () => {
    expect(resolveSubjectAfterPreview("Hello {{ name }}", "Hello Ada", false)).toBe("Hello Ada");
  });

  it("keeps manual override when the user has edited the field", () => {
    expect(resolveSubjectAfterPreview("Özel test konusu", "Hello Ada", true)).toBe("Özel test konusu");
  });

  it("preserves empty override when the user cleared the field", () => {
    expect(resolveSubjectAfterPreview("", "Hello Ada", true)).toBe("");
  });
});

describe("selectActiveMailTemplates", () => {
  it("includes all active template types and excludes inactive or deleted", () => {
    const result = selectActiveMailTemplates([
      {
        id: "1",
        organization_id: "org",
        name: "Transactional",
        key: "tx",
        subject: "Konu",
        body_html: null,
        body_text: "text",
        template_type: "transactional",
        language: "tr",
        is_active: true,
        is_default: false,
        variables_schema: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: "2",
        organization_id: "org",
        name: "Marketing",
        key: "mk",
        subject: "Konu",
        body_html: null,
        body_text: "text",
        template_type: "marketing",
        language: "tr",
        is_active: true,
        is_default: true,
        variables_schema: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: "3",
        organization_id: "org",
        name: "Inactive",
        key: "in",
        subject: "Konu",
        body_html: null,
        body_text: "text",
        template_type: "notification",
        language: "tr",
        is_active: false,
        is_default: false,
        variables_schema: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: "4",
        organization_id: "org",
        name: "Deleted",
        key: "del",
        subject: "Konu",
        body_html: null,
        body_text: "text",
        template_type: "system",
        language: "en",
        is_active: true,
        is_default: false,
        variables_schema: null,
        created_at: "",
        updated_at: "",
        deleted_at: "2026-01-01T00:00:00Z",
      },
    ]);

    expect(result.map((item) => item.id)).toEqual(["2", "1"]);
  });
});

describe("formatMailTemplateOptionLabel", () => {
  it("includes type and language in the option label", () => {
    expect(
      formatMailTemplateOptionLabel({
        id: "1",
        organization_id: "org",
        name: "Fuar Daveti",
        key: "invite",
        subject: "Konu",
        body_html: null,
        body_text: null,
        template_type: "transactional",
        language: "tr",
        is_active: true,
        is_default: false,
        variables_schema: null,
        created_at: "",
        updated_at: "",
      }),
    ).toBe("Fuar Daveti (transactional · tr)");
  });
});
