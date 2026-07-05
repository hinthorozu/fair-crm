import { describe, expect, it } from "vitest";
import {
  buildCreateSmtpPayload,
  buildUpdateSmtpPayload,
  responseContainsPassword,
  validateSmtpFormValues,
  EMPTY_SMTP_FORM_VALUES,
} from "./smtpForm";

describe("validateSmtpFormValues", () => {
  it("accepts valid create values", () => {
    expect(
      validateSmtpFormValues({
        ...EMPTY_SMTP_FORM_VALUES,
        name: "Primary SMTP",
        from_email: "noreply@example.com",
        host: "smtp.example.com",
        port: "587",
      }),
    ).toBeNull();
  });

  it("rejects invalid email and port", () => {
    expect(
      validateSmtpFormValues({
        ...EMPTY_SMTP_FORM_VALUES,
        name: "Primary SMTP",
        from_email: "invalid",
        host: "smtp.example.com",
        port: "70000",
      }),
    ).toBe("Geçerli bir gönderen e-posta adresi girin.");
  });
});

describe("buildCreateSmtpPayload", () => {
  it("builds expected create payload", () => {
    expect(
      buildCreateSmtpPayload({
        ...EMPTY_SMTP_FORM_VALUES,
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
    });
  });
});

describe("buildUpdateSmtpPayload", () => {
  it("omits password when blank to preserve existing secret", () => {
    const payload = buildUpdateSmtpPayload({
      ...EMPTY_SMTP_FORM_VALUES,
      name: "Primary SMTP",
      from_email: "noreply@example.com",
      host: "smtp.example.com",
      port: "587",
      password: "   ",
    });

    expect(payload.password).toBeUndefined();
  });

  it("includes password when a new value is provided", () => {
    const payload = buildUpdateSmtpPayload({
      ...EMPTY_SMTP_FORM_VALUES,
      name: "Primary SMTP",
      from_email: "noreply@example.com",
      host: "smtp.example.com",
      port: "587",
      password: "new-secret",
    });

    expect(payload.password).toBe("new-secret");
  });
});

describe("responseContainsPassword", () => {
  it("detects password field in API payloads", () => {
    expect(responseContainsPassword({ id: "1", password: "secret" })).toBe(true);
    expect(responseContainsPassword({ id: "1", has_password: true })).toBe(false);
  });
});
