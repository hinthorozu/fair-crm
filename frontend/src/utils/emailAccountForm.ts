import { adminLabels } from "../labels/adminLabels";
import type {
  CreateEmailAccountPayload,
  EmailAccount,
  SmtpEncryptionType,
  UpdateEmailAccountPayload,
} from "../types/smtp";

export const SMTP_ENCRYPTION_TYPES: SmtpEncryptionType[] = [
  "none",
  "ssl",
  "tls",
  "starttls",
];

const SSL_PORT = 465;
const STARTTLS_PORT = 587;

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
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function emailAccountToFormValues(account: EmailAccount): EmailAccountFormValues {
  return {
    name: account.name,
    from_email: account.from_email,
    from_name: account.from_name ?? "",
    host: account.host,
    port: String(account.port),
    username: account.username ?? "",
    password: "",
    encryption_type: account.encryption_type,
    is_default: account.is_default,
    is_active: account.is_active,
    max_delivery_attempts: String(account.max_delivery_attempts ?? 3),
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

export function validateEmailAccountFormValues(
  values: EmailAccountFormValues,
  mode: "create" | "edit" = "create",
): string | null {
  if (!values.name.trim()) {
    return "SMTP adı zorunludur.";
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
  if (mode === "create") {
    const attempts = Number(values.max_delivery_attempts);
    if (!Number.isInteger(attempts) || attempts < 1 || attempts > 5) {
      return adminLabels.smtpMaxDeliveryAttemptsInvalid;
    }
  }
  return null;
}

export function buildCreateEmailAccountPayload(
  values: EmailAccountFormValues,
): CreateEmailAccountPayload {
  return {
    name: values.name.trim(),
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
): UpdateEmailAccountPayload {
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
