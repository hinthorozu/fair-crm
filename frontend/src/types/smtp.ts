export type SmtpEncryptionType = "none" | "ssl" | "tls" | "starttls";

/** Delivery account type — SMTP or generic provider (e.g. MailerSend). */
export type EmailAccountType = "smtp" | "provider";

export type ErrorPolicyCategory = "ACCOUNT_ERROR" | "DELIVERY_ERROR" | "MESSAGE_ERROR";

export type AccountErrorAction = "fail" | "deactivate_and_fail" | "record_and_fail";
export type DeliveryErrorAction = "auto_retry" | "fail";
export type MessageErrorAction = "fail" | "skip";

export interface ErrorPolicyGroup {
  category: ErrorPolicyCategory;
  identifiers: string[];
  action: string;
}

export interface ErrorPolicy {
  groups: ErrorPolicyGroup[];
}

export interface ProviderFieldDefinition {
  key: string;
  label: string;
  type: string;
  required: boolean;
  secret: boolean;
  placeholder?: string | null;
  help_text?: string | null;
}

export interface EmailAccountProviderDefinition {
  provider_key: string;
  display_name: string;
  fields: ProviderFieldDefinition[];
}

export interface EmailAccountProviderListResponse {
  items: EmailAccountProviderDefinition[];
}

export interface EmailAccount {
  id: string;
  organization_id: string;
  name: string;
  /** Present when API exposes EmailAccount typing; defaults to smtp for current API. */
  account_type?: EmailAccountType;
  provider_key?: string | null;
  provider_config?: Record<string, string | null> | null;
  secrets_set?: Record<string, boolean>;
  error_policy?: ErrorPolicy | null;
  from_email: string;
  from_name: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  encryption_type?: SmtpEncryptionType | null;
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
  account_type?: EmailAccountType;
  provider_key?: string | null;
  provider_config?: Record<string, string>;
  error_policy?: ErrorPolicy;
  from_email?: string | null;
  from_name?: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string | null;
  encryption_type?: SmtpEncryptionType;
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
  from_email?: string | null;
  from_name?: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string;
  encryption_type?: SmtpEncryptionType;
  is_default?: boolean;
  is_active?: boolean;
  max_delivery_attempts?: number;
  provider_key?: string | null;
  provider_config?: Record<string, string>;
  error_policy?: ErrorPolicy;
}
