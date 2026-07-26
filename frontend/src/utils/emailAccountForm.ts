import { adminLabels } from "../labels/adminLabels";
import type {
  CreateEmailAccountPayload,
  EmailAccount,
  EmailAccountProviderDefinition,
  EmailAccountType,
  ErrorPolicy,
  ErrorPolicyCategory,
  ProviderFieldDefinition,
  SmtpEncryptionType,
  UpdateEmailAccountPayload,
} from "../types/smtp";

export const SMTP_ENCRYPTION_TYPES: SmtpEncryptionType[] = [
  "none",
  "ssl",
  "tls",
  "starttls",
];

export const ERROR_POLICY_CATEGORIES: ErrorPolicyCategory[] = [
  "ACCOUNT_ERROR",
  "DELIVERY_ERROR",
  "MESSAGE_ERROR",
];

export const ERROR_POLICY_ACTIONS_BY_CATEGORY: Record<ErrorPolicyCategory, readonly string[]> = {
  ACCOUNT_ERROR: ["fail", "deactivate_and_fail", "record_and_fail"],
  DELIVERY_ERROR: ["auto_retry", "fail"],
  MESSAGE_ERROR: ["fail", "skip"],
};

export const DEFAULT_ERROR_POLICY_ACTIONS: Record<ErrorPolicyCategory, string> = {
  ACCOUNT_ERROR: "fail",
  DELIVERY_ERROR: "fail",
  MESSAGE_ERROR: "fail",
};

const SSL_PORT = 465;
const STARTTLS_PORT = 587;

export interface ErrorPolicyGroupFormValues {
  category: ErrorPolicyCategory;
  identifiersText: string;
  action: string;
}

export interface EmailAccountFormValues {
  name: string;
  from_email: string;
  from_name: string;
  host: string;
  port: string;
  username: string;
  password: string;
  encryption_type: SmtpEncryptionType;
  is_default: boolean;
  is_active: boolean;
  max_delivery_attempts: string;
  provider_key: string;
  provider_config: Record<string, string>;
  error_policy_groups: ErrorPolicyGroupFormValues[];
}

export function defaultErrorPolicyGroups(): ErrorPolicyGroupFormValues[] {
  return ERROR_POLICY_CATEGORIES.map((category) => ({
    category,
    identifiersText: "",
    action: DEFAULT_ERROR_POLICY_ACTIONS[category],
  }));
}

export const EMPTY_EMAIL_ACCOUNT_FORM_VALUES: EmailAccountFormValues = {
  name: "",
  from_email: "",
  from_name: "",
  host: "",
  port: "587",
  username: "",
  password: "",
  encryption_type: "starttls",
  is_default: false,
  is_active: true,
  max_delivery_attempts: "3",
  provider_key: "",
  provider_config: {},
  error_policy_groups: defaultErrorPolicyGroups(),
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Normalize comma/semicolon-separated identifiers: trim, drop empties, dedupe (order-preserving). */
export function normalizeErrorIdentifiers(raw: string | string[] | null | undefined): string[] {
  if (raw == null) {
    return [];
  }
  const parts: string[] = [];
  if (typeof raw === "string") {
    parts.push(...raw.replace(/;/g, ",").split(","));
  } else {
    for (const item of raw) {
      if (item == null) continue;
      parts.push(...String(item).replace(/;/g, ",").split(","));
    }
  }

  const seen = new Set<string>();
  const result: string[] = [];
  for (const part of parts) {
    const token = part.trim();
    if (!token || seen.has(token)) continue;
    seen.add(token);
    result.push(token);
  }
  return result;
}

export function errorPolicyToFormGroups(
  errorPolicy: EmailAccount["error_policy"] | null | undefined,
): ErrorPolicyGroupFormValues[] {
  const byCategory = new Map<ErrorPolicyCategory, ErrorPolicyGroupFormValues>();
  for (const group of errorPolicy?.groups ?? []) {
    const category = group.category as ErrorPolicyCategory;
    if (!ERROR_POLICY_CATEGORIES.includes(category)) continue;
    byCategory.set(category, {
      category,
      identifiersText: (group.identifiers ?? []).join(", "),
      action: group.action || DEFAULT_ERROR_POLICY_ACTIONS[category],
    });
  }
  return ERROR_POLICY_CATEGORIES.map(
    (category) =>
      byCategory.get(category) ?? {
        category,
        identifiersText: "",
        action: DEFAULT_ERROR_POLICY_ACTIONS[category],
      },
  );
}

export function buildErrorPolicyPayload(groups: ErrorPolicyGroupFormValues[]): ErrorPolicy {
  return {
    groups: groups.map((group) => ({
      category: group.category,
      identifiers: normalizeErrorIdentifiers(group.identifiersText),
      action: group.action || DEFAULT_ERROR_POLICY_ACTIONS[group.category],
    })),
  };
}

export function providerConfigToFormValues(
  config: EmailAccount["provider_config"] | null | undefined,
  fields?: ProviderFieldDefinition[],
): Record<string, string> {
  const result: Record<string, string> = {};
  if (fields) {
    for (const field of fields) {
      if (field.secret) {
        result[field.key] = "";
        continue;
      }
      const value = config?.[field.key];
      result[field.key] = value == null ? "" : String(value);
    }
    return result;
  }
  if (!config) return result;
  for (const [key, value] of Object.entries(config)) {
    result[key] = value == null ? "" : String(value);
  }
  return result;
}

export function emailAccountToFormValues(
  account: EmailAccount,
  providerDefinition?: EmailAccountProviderDefinition | null,
): EmailAccountFormValues {
  return {
    name: account.name,
    from_email: account.from_email,
    from_name: account.from_name ?? "",
    host: account.host ?? "",
    port: account.port != null ? String(account.port) : "587",
    username: account.username ?? "",
    password: "",
    encryption_type: account.encryption_type ?? "starttls",
    is_default: account.is_default,
    is_active: account.is_active,
    max_delivery_attempts: String(account.max_delivery_attempts ?? 3),
    provider_key: account.provider_key ?? "",
    provider_config: providerConfigToFormValues(
      account.provider_config,
      providerDefinition?.fields,
    ),
    error_policy_groups: errorPolicyToFormGroups(account.error_policy),
  };
}

export function emailAccountPasswordSet(
  account: Pick<EmailAccount, "password_set" | "has_password">,
): boolean {
  return account.password_set ?? account.has_password ?? false;
}

export function getSmtpPortEncryptionHints(
  portValue: string,
  encryptionType: SmtpEncryptionType,
): string[] {
  const port = Number(portValue);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return [];
  }

  const hints = new Set<string>();

  if (encryptionType === "ssl") {
    hints.add(adminLabels.smtpHintSslPort);
    if (port !== SSL_PORT) {
      hints.add(adminLabels.smtpHintUseSslOn465);
    }
  }

  if (encryptionType === "starttls") {
    hints.add(adminLabels.smtpHintStarttlsPort);
    if (port !== STARTTLS_PORT) {
      hints.add(adminLabels.smtpHintUseStarttlsOn587);
    }
  }

  if (port === STARTTLS_PORT && encryptionType === "ssl") {
    hints.add(adminLabels.smtpHintUseStarttlsOn587);
  }

  if (port === SSL_PORT && encryptionType === "starttls") {
    hints.add(adminLabels.smtpHintUseSslOn465);
  }

  return Array.from(hints);
}

export function formatSmtpTestMailError(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("wrong_version_number")) {
    return (
      "SMTP SSL bağlantı hatası: Şifreleme türü ile port uyumsuz olabilir. " +
      "SSL için 465, STARTTLS için 587 deneyin."
    );
  }
  if (
    normalized.includes("smtp connection failed:") ||
    normalized.includes("smtp delivery failed:")
  ) {
    return adminLabels.smtpTestMailError;
  }
  return message;
}

function validateMaxDeliveryAttempts(values: EmailAccountFormValues): string | null {
  const attempts = Number(values.max_delivery_attempts);
  if (!Number.isInteger(attempts) || attempts < 1 || attempts > 5) {
    return adminLabels.smtpMaxDeliveryAttemptsInvalid;
  }
  return null;
}

function validateErrorPolicyGroups(groups: ErrorPolicyGroupFormValues[]): string | null {
  const identifierOwners = new Map<string, ErrorPolicyCategory>();

  for (const group of groups) {
    const allowed = ERROR_POLICY_ACTIONS_BY_CATEGORY[group.category];
    if (!allowed?.includes(group.action)) {
      return adminLabels.smtpErrorPolicyInvalidAction;
    }
    const identifiers = normalizeErrorIdentifiers(group.identifiersText);
    for (const identifier of identifiers) {
      const owner = identifierOwners.get(identifier);
      if (owner != null && owner !== group.category) {
        return adminLabels.smtpErrorPolicyDuplicateIdentifier.replace(
          "{identifier}",
          identifier,
        );
      }
      identifierOwners.set(identifier, group.category);
    }
  }
  return null;
}

function validateProviderConfigFields(
  values: EmailAccountFormValues,
  mode: "create" | "edit",
  definition: EmailAccountProviderDefinition,
  secretsSet: Record<string, boolean> | undefined,
): string | null {
  for (const field of definition.fields) {
    const raw = values.provider_config[field.key] ?? "";
    const value = raw.trim();

    if (field.secret) {
      if (mode === "create" && field.required && !value) {
        return adminLabels.smtpProviderFieldRequired.replace("{field}", field.label);
      }
      if (mode === "edit" && field.required && !value && !secretsSet?.[field.key]) {
        return adminLabels.smtpProviderFieldRequired.replace("{field}", field.label);
      }
      continue;
    }

    if (field.required && !value) {
      return adminLabels.smtpProviderFieldRequired.replace("{field}", field.label);
    }
    if (value && (field.type === "email" || field.key === "from_email") && !EMAIL_PATTERN.test(value)) {
      return adminLabels.smtpProviderFieldInvalidEmail.replace("{field}", field.label);
    }
  }
  return null;
}

export interface ValidateEmailAccountFormOptions {
  accountType?: EmailAccountType;
  providerDefinition?: EmailAccountProviderDefinition | null;
  secretsSet?: Record<string, boolean>;
}

export function validateEmailAccountFormValues(
  values: EmailAccountFormValues,
  mode: "create" | "edit" = "create",
  options: ValidateEmailAccountFormOptions = {},
): string | null {
  const accountType = options.accountType ?? "smtp";

  if (!values.name.trim()) {
    return accountType === "provider"
      ? adminLabels.smtpProviderNameRequired
      : "SMTP adı zorunludur.";
  }

  const attemptsError = validateMaxDeliveryAttempts(values);
  if (attemptsError) return attemptsError;

  if (accountType === "provider") {
    if (!values.provider_key.trim()) {
      return adminLabels.smtpProviderKeyRequired;
    }
    if (!options.providerDefinition) {
      return adminLabels.smtpProviderDefinitionMissing;
    }
    const configError = validateProviderConfigFields(
      values,
      mode,
      options.providerDefinition,
      options.secretsSet,
    );
    if (configError) return configError;
    return validateErrorPolicyGroups(values.error_policy_groups);
  }

  if (!values.from_email.trim() || !EMAIL_PATTERN.test(values.from_email.trim())) {
    return "Geçerli bir gönderen e-posta adresi girin.";
  }
  if (!values.host.trim()) {
    return "Sunucu (host) zorunludur.";
  }
  const port = Number(values.port);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return "Port 1–65535 arasında bir sayı olmalıdır.";
  }
  if (!SMTP_ENCRYPTION_TYPES.includes(values.encryption_type)) {
    return "Geçersiz şifreleme türü.";
  }
  return null;
}

function buildProviderConfigPayload(
  values: EmailAccountFormValues,
  definition: EmailAccountProviderDefinition | null | undefined,
  mode: "create" | "edit",
): Record<string, string> {
  const payload: Record<string, string> = {};
  const fields = definition?.fields;
  if (fields) {
    for (const field of fields) {
      const value = (values.provider_config[field.key] ?? "").trim();
      if (field.secret) {
        if (value) {
          payload[field.key] = value;
        } else if (mode === "create") {
          payload[field.key] = "";
        }
        // edit + blank → omit to preserve
        continue;
      }
      payload[field.key] = value;
    }
    return payload;
  }
  for (const [key, raw] of Object.entries(values.provider_config)) {
    const value = raw.trim();
    if (value) {
      payload[key] = value;
    }
  }
  return payload;
}

export function buildCreateEmailAccountPayload(
  values: EmailAccountFormValues,
  accountType: EmailAccountType = "smtp",
  providerDefinition?: EmailAccountProviderDefinition | null,
): CreateEmailAccountPayload {
  if (accountType === "provider") {
    return {
      name: values.name.trim(),
      account_type: "provider",
      provider_key: values.provider_key.trim(),
      provider_config: buildProviderConfigPayload(values, providerDefinition, "create"),
      error_policy: buildErrorPolicyPayload(values.error_policy_groups),
      is_default: values.is_default,
      is_active: values.is_active,
      max_delivery_attempts: Number(values.max_delivery_attempts),
    };
  }

  return {
    name: values.name.trim(),
    account_type: "smtp",
    from_email: values.from_email.trim(),
    from_name: values.from_name.trim() || null,
    host: values.host.trim(),
    port: Number(values.port),
    username: values.username.trim() || null,
    password: values.password || null,
    encryption_type: values.encryption_type,
    is_default: values.is_default,
    is_active: values.is_active,
    max_delivery_attempts: Number(values.max_delivery_attempts),
  };
}

export function buildUpdateEmailAccountPayload(
  values: EmailAccountFormValues,
  accountType: EmailAccountType = "smtp",
  providerDefinition?: EmailAccountProviderDefinition | null,
): UpdateEmailAccountPayload {
  if (accountType === "provider") {
    return {
      name: values.name.trim(),
      is_default: values.is_default,
      is_active: values.is_active,
      max_delivery_attempts: Number(values.max_delivery_attempts),
      provider_config: buildProviderConfigPayload(values, providerDefinition, "edit"),
      error_policy: buildErrorPolicyPayload(values.error_policy_groups),
    };
  }

  const payload: UpdateEmailAccountPayload = {
    name: values.name.trim(),
    from_email: values.from_email.trim(),
    from_name: values.from_name.trim() || null,
    host: values.host.trim(),
    port: Number(values.port),
    username: values.username.trim() || null,
    encryption_type: values.encryption_type,
    is_default: values.is_default,
    is_active: values.is_active,
    max_delivery_attempts: Number(values.max_delivery_attempts),
  };
  if (values.password.trim()) {
    payload.password = values.password;
  }
  return payload;
}

export function responseContainsPassword(value: unknown): boolean {
  if (!value || typeof value !== "object") {
    return false;
  }
  return "password" in value;
}

/** Map provider_key → registry display_name for list cells. */
export function buildProviderDisplayNameMap(
  providers: ReadonlyArray<Pick<EmailAccountProviderDefinition, "provider_key" | "display_name">>,
): Map<string, string> {
  return new Map(
    providers.map((provider) => [provider.provider_key, provider.display_name] as const),
  );
}

/**
 * SMTP: host. Provider: Provider Registry display_name (fallback: provider_key).
 */
export function resolveEmailAccountServerOrProviderLabel(
  account: Pick<EmailAccount, "account_type" | "host" | "provider_key">,
  providerDisplayNames: ReadonlyMap<string, string>,
): string {
  if (account.account_type === "provider") {
    const key = account.provider_key?.trim();
    if (!key) return "—";
    return providerDisplayNames.get(key) || key;
  }
  return account.host?.trim() || "—";
}
