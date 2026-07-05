import type {
  CreateSmtpAccountPayload,
  SmtpAccount,
  SmtpEncryptionType,
  UpdateSmtpAccountPayload,
} from "../types/smtp";

export const SMTP_ENCRYPTION_TYPES: SmtpEncryptionType[] = [
  "none",
  "ssl",
  "tls",
  "starttls",
];

export interface SmtpAccountFormValues {
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
}

export const EMPTY_SMTP_FORM_VALUES: SmtpAccountFormValues = {
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
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function smtpAccountToFormValues(account: SmtpAccount): SmtpAccountFormValues {
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
  };
}

export function smtpPasswordSet(account: Pick<SmtpAccount, "password_set" | "has_password">): boolean {
  return account.password_set ?? account.has_password ?? false;
}

export function validateSmtpFormValues(values: SmtpAccountFormValues): string | null {
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
  return null;
}

export function buildCreateSmtpPayload(values: SmtpAccountFormValues): CreateSmtpAccountPayload {
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
  };
}

export function buildUpdateSmtpPayload(values: SmtpAccountFormValues): UpdateSmtpAccountPayload {
  const payload: UpdateSmtpAccountPayload = {
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
