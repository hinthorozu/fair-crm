export type MailTemplateType = "transactional" | "notification" | "marketing" | "system";

export interface MailTemplate {
  id: string;
  organization_id: string;
  name: string;
  key: string;
  subject: string;
  body_html: string | null;
  body_text: string | null;
  template_type: MailTemplateType;
  language: string;
  is_active: boolean;
  is_default: boolean;
  variables_schema: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export type MailTemplateListItem = MailTemplate;

export interface MailTemplateListResponse {
  items: MailTemplateListItem[];
}

export interface CreateMailTemplatePayload {
  name: string;
  key: string;
  subject: string;
  body_html?: string | null;
  body_text?: string | null;
  template_type: MailTemplateType;
  language: string;
  is_active: boolean;
  is_default: boolean;
  variables_schema?: Record<string, unknown> | null;
}

export interface UpdateMailTemplatePayload {
  name?: string;
  key?: string;
  subject?: string;
  body_html?: string | null;
  body_text?: string | null;
  template_type?: MailTemplateType;
  language?: string;
  is_active?: boolean;
  is_default?: boolean;
  variables_schema?: Record<string, unknown> | null;
}

export interface RenderMailTemplatePayload {
  variables: Record<string, unknown>;
}

export interface RenderMailTemplateResponse {
  subject: string;
  body_html: string | null;
  body_text: string | null;
}

export interface SendTestMailTemplatePayload {
  to_email: string;
  smtp_account_id?: string | null;
  variables: Record<string, unknown>;
  subject_override?: string | null;
}

export interface SendTestMailTemplateResponse {
  success: boolean;
  message: string;
  smtp_host?: string | null;
  smtp_port?: number | null;
  template_key?: string | null;
}
