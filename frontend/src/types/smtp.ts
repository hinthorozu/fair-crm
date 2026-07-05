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
  has_password: boolean;
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
