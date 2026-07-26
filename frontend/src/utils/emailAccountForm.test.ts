import { describe, expect, it } from "vitest";
import type { EmailAccountProviderDefinition } from "../types/smtp";
import {
  buildCreateEmailAccountPayload,
  buildUpdateEmailAccountPayload,
  buildErrorPolicyPayload,
  buildProviderDisplayNameMap,
  defaultErrorPolicyGroups,
  normalizeErrorIdentifiers,
  responseContainsPassword,
  resolveEmailAccountServerOrProviderLabel,
  validateEmailAccountFormValues,
  EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
  getSmtpPortEncryptionHints,
  formatSmtpTestMailError,
  emailAccountToFormValues,
} from "./emailAccountForm";

const MAILERSEND_DEFINITION: EmailAccountProviderDefinition = {
  provider_key: "mailersend",
  display_name: "MailerSend",
  fields: [
    {
      key: "api_token",
      label: "API Token",
      type: "password",
      required: true,
      secret: true,
      placeholder: "MailerSend API token",
    },
    {
      key: "from_email",
      label: "Gönderen E-Mail",
      type: "email",
      required: true,
      secret: false,
    },
    {
      key: "from_name",
      label: "Gönderen Adı",
      type: "text",
      required: true,
      secret: false,
    },
  ],
};

function providerFormValues(
  overrides: Partial<typeof EMPTY_EMAIL_ACCOUNT_FORM_VALUES> = {},
) {
  return {
    ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
    name: "MailerSend Primary",
    provider_key: "mailersend",
    provider_config: {
      api_token: "token-123",
      from_email: "noreply@example.com",
      from_name: "FAIR CRM",
    },
    error_policy_groups: defaultErrorPolicyGroups(),
    ...overrides,
  };
}

describe("normalizeErrorIdentifiers", () => {
  it("trims, splits, and dedupes identifiers", () => {
    expect(normalizeErrorIdentifiers(" 401, 429; 401 , 422 ")).toEqual(["401", "429", "422"]);
  });
});

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

  it("rejects invalid max_delivery_attempts on edit", () => {
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
    ).toBe("Başarısız gönderim deneme sayısı 1–5 arasında olmalıdır.");
  });

  it("accepts valid provider create values", () => {
    expect(
      validateEmailAccountFormValues(providerFormValues(), "create", {
        accountType: "provider",
        providerDefinition: MAILERSEND_DEFINITION,
      }),
    ).toBeNull();
  });

  it("rejects provider create without api token", () => {
    expect(
      validateEmailAccountFormValues(
        providerFormValues({
          provider_config: {
            api_token: "",
            from_email: "noreply@example.com",
            from_name: "FAIR CRM",
          },
        }),
        "create",
        {
          accountType: "provider",
          providerDefinition: MAILERSEND_DEFINITION,
        },
      ),
    ).toContain("API Token");
  });

  it("allows blank secret on edit when secrets_set is true", () => {
    expect(
      validateEmailAccountFormValues(
        providerFormValues({
          provider_config: {
            api_token: "",
            from_email: "noreply@example.com",
            from_name: "FAIR CRM",
          },
        }),
        "edit",
        {
          accountType: "provider",
          providerDefinition: MAILERSEND_DEFINITION,
          secretsSet: { api_token: true },
        },
      ),
    ).toBeNull();
  });

  it("rejects cross-group duplicate error identifiers", () => {
    const groups = defaultErrorPolicyGroups().map((group) =>
      group.category === "ACCOUNT_ERROR"
        ? { ...group, identifiersText: "401, 429" }
        : group.category === "DELIVERY_ERROR"
          ? { ...group, identifiersText: "429" }
          : group,
    );
    expect(
      validateEmailAccountFormValues(providerFormValues({ error_policy_groups: groups }), "create", {
        accountType: "provider",
        providerDefinition: MAILERSEND_DEFINITION,
      }),
    ).toContain("429");
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
      account_type: "smtp",
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

  it("builds provider create payload with error policy", () => {
    const groups = defaultErrorPolicyGroups().map((group) =>
      group.category === "ACCOUNT_ERROR"
        ? { ...group, identifiersText: "401, 403", action: "deactivate_and_fail" }
        : group,
    );
    expect(
      buildCreateEmailAccountPayload(
        providerFormValues({ error_policy_groups: groups }),
        "provider",
        MAILERSEND_DEFINITION,
      ),
    ).toEqual({
      name: "MailerSend Primary",
      account_type: "provider",
      provider_key: "mailersend",
      provider_config: {
        api_token: "token-123",
        from_email: "noreply@example.com",
        from_name: "FAIR CRM",
      },
      error_policy: {
        groups: [
          {
            category: "ACCOUNT_ERROR",
            identifiers: ["401", "403"],
            action: "deactivate_and_fail",
          },
          { category: "DELIVERY_ERROR", identifiers: [], action: "fail" },
          { category: "MESSAGE_ERROR", identifiers: [], action: "fail" },
        ],
      },
      is_default: false,
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
      max_delivery_attempts: "4",
    });

    expect(payload.password).toBeUndefined();
    expect(payload.max_delivery_attempts).toBe(4);
  });

  it("includes password when a new value is provided", () => {
    const payload = buildUpdateEmailAccountPayload({
      ...EMPTY_EMAIL_ACCOUNT_FORM_VALUES,
      name: "Primary SMTP",
      from_email: "noreply@example.com",
      host: "smtp.example.com",
      port: "587",
      password: "new-secret",
      max_delivery_attempts: "2",
    });

    expect(payload.password).toBe("new-secret");
    expect(payload.max_delivery_attempts).toBe(2);
  });

  it("omits blank provider secret on update", () => {
    const payload = buildUpdateEmailAccountPayload(
      providerFormValues({
        provider_config: {
          api_token: "",
          from_email: "noreply@example.com",
          from_name: "FAIR CRM",
        },
        max_delivery_attempts: "5",
      }),
      "provider",
      MAILERSEND_DEFINITION,
    );

    expect(payload.provider_config).toEqual({
      from_email: "noreply@example.com",
      from_name: "FAIR CRM",
    });
    expect(payload.error_policy).toEqual(buildErrorPolicyPayload(defaultErrorPolicyGroups()));
    expect(payload.max_delivery_attempts).toBe(5);
  });
});

describe("emailAccountToFormValues", () => {
  it("maps provider account with nulled secrets and error policy", () => {
    const values = emailAccountToFormValues(
      {
        id: "1",
        organization_id: "org",
        name: "MS",
        account_type: "provider",
        provider_key: "mailersend",
        provider_config: {
          api_token: null,
          from_email: "a@b.com",
          from_name: "N",
        },
        secrets_set: { api_token: true },
        error_policy: {
          groups: [
            { category: "ACCOUNT_ERROR", identifiers: ["401"], action: "fail" },
            { category: "DELIVERY_ERROR", identifiers: ["429"], action: "auto_retry" },
            { category: "MESSAGE_ERROR", identifiers: [], action: "skip" },
          ],
        },
        from_email: "a@b.com",
        from_name: "N",
        host: null,
        port: null,
        username: null,
        encryption_type: null,
        is_default: false,
        is_active: true,
        password_set: false,
        max_delivery_attempts: 3,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      MAILERSEND_DEFINITION,
    );

    expect(values.provider_config.api_token).toBe("");
    expect(values.provider_config.from_email).toBe("a@b.com");
    expect(values.error_policy_groups[0].identifiersText).toBe("401");
    expect(values.error_policy_groups[1].action).toBe("auto_retry");
    expect(values.error_policy_groups[2].action).toBe("skip");
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

describe("resolveEmailAccountServerOrProviderLabel", () => {
  const providerNames = buildProviderDisplayNameMap([MAILERSEND_DEFINITION]);

  it("shows SMTP host for smtp accounts", () => {
    expect(
      resolveEmailAccountServerOrProviderLabel(
        { account_type: "smtp", host: "smtp.yandex.com.tr", provider_key: null },
        providerNames,
      ),
    ).toBe("smtp.yandex.com.tr");
  });

  it("shows registry display_name for provider accounts", () => {
    expect(
      resolveEmailAccountServerOrProviderLabel(
        { account_type: "provider", host: null, provider_key: "mailersend" },
        providerNames,
      ),
    ).toBe("MailerSend");
  });

  it("falls back to provider_key when definition is missing", () => {
    expect(
      resolveEmailAccountServerOrProviderLabel(
        { account_type: "provider", host: null, provider_key: "unknown_provider" },
        providerNames,
      ),
    ).toBe("unknown_provider");
  });
});
