import { describe, expect, it } from "vitest";
import {
  buildCreateEmailAccountPayload,
  buildUpdateEmailAccountPayload,
  responseContainsPassword,
  validateEmailAccountFormValues,
  EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
  getSmtpPortEncryptionHints,
  formatSmtpTestMailError,
} from "./emailAccountForm";

describe("validateEmailAccountFormValues", () => {
  it("accepts valid create values", () => {
    expect(
      validateEmailAccountFormValues({
        ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
        name: "Primary SMTP",
        from_email: "noreply@example.com",
        host: "smtp.example.com",
        port: "587",
        max_delivery_attempts: "3",
      }),
    ).toBeNull();
  });

  it("rejects invalid email and port", () => {
    expect(
      validateEmailAccountFormValues({
        ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
        name: "Primary SMTP",
        from_email: "invalid",
        host: "smtp.example.com",
        port: "70000",
      }),
    ).toBe("Geçerli bir gönderen e-posta adresi girin.");
  });

  it("rejects invalid max_delivery_attempts on create", () => {
    expect(
      validateEmailAccountFormValues(
        {
          ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
          name: "Primary SMTP",
          from_email: "noreply@example.com",
          host: "smtp.example.com",
          port: "587",
          max_delivery_attempts: "9",
        },
        "create",
      ),
    ).toBe("Başarısız gönderim deneme sayısı 1–5 arasında olmalıdır.");
  });

  it("skips max_delivery_attempts validation on edit", () => {
    expect(
      validateEmailAccountFormValues(
        {
          ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
          name: "Primary SMTP",
          from_email: "noreply@example.com",
          host: "smtp.example.com",
          port: "587",
          max_delivery_attempts: "9",
        },
        "edit",
      ),
    ).toBeNull();
  });
});

describe("buildCreateEmailAccountPayload", () => {
  it("builds expected create payload", () => {
    expect(
      buildCreateEmailAccountPayload({
        ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
        name: " Primary ",
        from_email: "noreply@example.com",
        from_name: "FAIR CRM",
        host: "smtp.example.com",
        port: "587",
        username: "user",
        password: "secret",
        encryption_type: "starttls",
        is_default: true,
        is_active: true,
        max_delivery_attempts: "3",
      }),
    ).toEqual({
      name: "Primary",
      from_email: "noreply@example.com",
      from_name: "FAIR CRM",
      host: "smtp.example.com",
      port: 587,
      username: "user",
      password: "secret",
      encryption_type: "starttls",
      is_default: true,
      is_active: true,
      max_delivery_attempts: 3,
    });
  });
});

describe("buildUpdateEmailAccountPayload", () => {
  it("omits password when blank to preserve existing secret", () => {
    const payload = buildUpdateEmailAccountPayload({
      ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
      name: "Primary SMTP",
      from_email: "noreply@example.com",
      host: "smtp.example.com",
      port: "587",
      password: "   ",
    });

    expect(payload.password).toBeUndefined();
    expect("max_delivery_attempts" in payload).toBe(false);
  });

  it("includes password when a new value is provided", () => {
    const payload = buildUpdateEmailAccountPayload({
      ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
      name: "Primary SMTP",
      from_email: "noreply@example.com",
      host: "smtp.example.com",
      port: "587",
      password: "new-secret",
    });

    expect(payload.password).toBe("new-secret");
    expect("max_delivery_attempts" in payload).toBe(false);
  });
});

describe("responseContainsPassword", () => {
  it("detects password field in API payloads", () => {
    expect(responseContainsPassword({ id: "1", password: "secret" })).toBe(true);
    expect(responseContainsPassword({ id: "1", has_password: true })).toBe(false);
  });
});

describe("getSmtpPortEncryptionHints", () => {
  it("warns when ssl is used with port 587", () => {
    const hints = getSmtpPortEncryptionHints("587", "ssl");
    expect(hints.some((hint) => hint.includes("465"))).toBe(true);
    expect(hints.some((hint) => hint.includes("starttls"))).toBe(true);
  });

  it("does not warn for starttls on port 587", () => {
    expect(getSmtpPortEncryptionHints("587", "starttls").some((hint) => hint.includes("465"))).toBe(
      false,
    );
  });
});

describe("formatSmtpTestMailError", () => {
  it("maps raw ssl wrong version errors to a friendly message", () => {
    expect(
      formatSmtpTestMailError(
        "SMTP connection failed: [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1082)",
      ),
    ).toContain("SSL için 465");
  });
});
