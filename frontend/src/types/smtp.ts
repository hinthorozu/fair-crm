export type SmtpEncryptionType = "none" | "ssl" | "tls" | "starttls";

export interface SmtpAccount {
  id: string;
  organization_id: string;
  name: string;
  from_email: string;
  from_name: string | null;
  host: string;
  port: number;
  username: string | null;
  encryption_type: SmtpEncryptionType;
  is_default: boolean;
  is_active: boolean;
  password_set: boolean;
  /** @deprecated use password_set */
  has_password?: boolean;
  config_warnings?: string[];
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface SmtpAccountListResponse {
  items: SmtpAccount[];
}

export interface CreateSmtpAccountPayload {
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
}

export interface SendTestSmtpMailPayload {
  recipient: string;
}

export interface SendTestSmtpMailResponse {
  success: boolean;
  message: string;
}

export interface UpdateSmtpAccountPayload {
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
