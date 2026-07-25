export type SmtpEncryptionType = "none" | "ssl" | "tls" | "starttls";

/** Delivery account type — SMTP today; provider reserved for future accounts. */
export type EmailAccountType = "smtp" | "provider";

export interface EmailAccount {
  id: string;
  organization_id: string;
  name: string;
  /** Present when API exposes EmailAccount typing; defaults to smtp for current API. */
  account_type?: EmailAccountType;
  provider_key?: string | null;
  from_email: string;
  from_name: string | null;
  host: string;
  port: number;
  username: string | null;
  encryption_type: SmtpEncryptionType;
  is_default: boolean;
  is_active: boolean;
  max_delivery_attempts: number;
  password_set: boolean;
  /** @deprecated use password_set */
  has_password?: boolean;
  config_warnings?: string[];
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface EmailAccountListResponse {
  items: EmailAccount[];
}

export interface CreateEmailAccountPayload {
  name: string;
  from_email: string;
  from_name?: string | null;
  host: string;
  port: number;
  username?: string | null;
  password?: string | null;
  encryption_type: SmtpEncryptionType;
  is_default: boolean;
  is_active: boolean;
  max_delivery_attempts: number;
}

export interface SendTestEmailAccountPayload {
  recipient: string;
}

export interface SendTestEmailAccountResponse {
  success: boolean;
  message: string;
}

export interface UpdateEmailAccountPayload {
  name?: string;
  from_email?: string;
  from_name?: string | null;
  host?: string;
  port?: number;
  username?: string | null;
  password?: string;
  encryption_type?: SmtpEncryptionType;
  is_default?: boolean;
  is_active?: boolean;
}
