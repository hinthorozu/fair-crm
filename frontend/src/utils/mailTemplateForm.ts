import type {
  CreateMailTemplatePayload,
  MailTemplate,
  MailTemplateType,
  UpdateMailTemplatePayload,
} from "../types/mailTemplates";
import { ApiError } from "../api/client";

export const MAIL_TEMPLATE_TYPES: MailTemplateType[] = [
  "transactional",
  "notification",
  "marketing",
  "system",
];

/** Active, non-deleted templates for bulk-email and similar pickers. */
export function selectActiveMailTemplates(templates: MailTemplate[]): MailTemplate[] {
  return templates
    .filter((item) => item.is_active && !item.deleted_at)
    .sort((a, b) => {
      if (a.is_default !== b.is_default) {
        return a.is_default ? -1 : 1;
      }
      return a.name.localeCompare(b.name, "tr");
    });
}

export function formatMailTemplateOptionLabel(
  template: MailTemplate,
  defaultBadge?: string,
): string {
  const meta = `${template.template_type} · ${template.language}`;
  if (template.is_default && defaultBadge) {
    return `${template.name} (${meta}, ${defaultBadge})`;
  }
  return `${template.name} (${meta})`;
}

export const DEFAULT_RENDER_VARIABLES_JSON = `{
  "customer_name": "ABC Fuarcılık",
  "contact_first_name": "Ahmet",
  "fair_name": "IFM 2026",
  "sender_name": "KYROX"
}`;

const KEY_PATTERN = /^[a-z][a-z0-9_]*$/;

export interface MailTemplateFormValues {
  name: string;
  key: string;
  subject: string;
  body_html: string;
  body_text: string;
  template_type: MailTemplateType;
  language: string;
  is_active: boolean;
  is_default: boolean;
  variables_schema_json: string;
}

export const EMPTY_MAIL_TEMPLATE_FORM_VALUES: MailTemplateFormValues = {
  name: "",
  key: "",
  subject: "",
  body_html: "",
  body_text: "",
  template_type: "transactional",
  language: "tr",
  is_active: true,
  is_default: false,
  variables_schema_json: "",
};

export function mailTemplateToFormValues(template: MailTemplate): MailTemplateFormValues {
  return {
    name: template.name,
    key: template.key,
    subject: template.subject,
    body_html: template.body_html ?? "",
    body_text: template.body_text ?? "",
    template_type: template.template_type,
    language: template.language,
    is_active: template.is_active,
    is_default: template.is_default,
    variables_schema_json: template.variables_schema
      ? JSON.stringify(template.variables_schema, null, 2)
      : "",
  };
}

export function validateMailTemplateFormValues(values: MailTemplateFormValues): string | null {
  if (!values.name.trim()) {
    return "Şablon adı zorunludur.";
  }
  if (!values.key.trim()) {
    return "Şablon anahtarı (key) zorunludur.";
  }
  if (!KEY_PATTERN.test(values.key.trim())) {
    return "Key küçük harf ile başlamalı; yalnızca küçük harf, rakam ve alt çizgi içerebilir (ör. welcome_email).";
  }
  if (!values.subject.trim()) {
    return "Konu (subject) zorunludur.";
  }
  if (!values.body_html.trim() && !values.body_text.trim()) {
    return "HTML gövde veya düz metin gövdeden en az biri doldurulmalıdır.";
  }
  if (!MAIL_TEMPLATE_TYPES.includes(values.template_type)) {
    return "Geçersiz şablon türü.";
  }
  if (!values.language.trim()) {
    return "Dil kodu zorunludur.";
  }
  if (values.variables_schema_json.trim()) {
    try {
      JSON.parse(values.variables_schema_json);
    } catch {
      return "variables_schema geçerli JSON olmalıdır.";
    }
  }
  return null;
}

function parseVariablesSchema(json: string): Record<string, unknown> | null {
  const trimmed = json.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("variables_schema must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

export function buildCreateMailTemplatePayload(
  values: MailTemplateFormValues,
): CreateMailTemplatePayload {
  return {
    name: values.name.trim(),
    key: values.key.trim().toLowerCase(),
    subject: values.subject.trim(),
    body_html: values.body_html.trim() || null,
    body_text: values.body_text.trim() || null,
    template_type: values.template_type,
    language: values.language.trim(),
    is_active: values.is_active,
    is_default: values.is_default,
    variables_schema: values.variables_schema_json.trim()
      ? parseVariablesSchema(values.variables_schema_json)
      : null,
  };
}

export function buildUpdateMailTemplatePayload(
  values: MailTemplateFormValues,
  initial?: MailTemplate | null,
): UpdateMailTemplatePayload {
  const full = buildCreateMailTemplatePayload(values);
  if (!initial) {
    return full;
  }

  const payload: UpdateMailTemplatePayload = {};
  if (full.name !== initial.name) payload.name = full.name;
  if (full.key !== initial.key) payload.key = full.key;
  if (full.subject !== initial.subject) payload.subject = full.subject;
  if ((full.body_html ?? null) !== (initial.body_html ?? null)) payload.body_html = full.body_html;
  if ((full.body_text ?? null) !== (initial.body_text ?? null)) payload.body_text = full.body_text;
  if (full.template_type !== initial.template_type) payload.template_type = full.template_type;
  if (full.language !== initial.language) payload.language = full.language;
  if (full.is_active !== initial.is_active) payload.is_active = full.is_active;
  if (full.is_default !== initial.is_default) payload.is_default = full.is_default;

  const initialSchema = initial.variables_schema
    ? JSON.stringify(initial.variables_schema)
    : "";
  const nextSchema = values.variables_schema_json.trim();
  if (nextSchema !== initialSchema) {
    payload.variables_schema = full.variables_schema ?? null;
  }

  return payload;
}

export function parseRenderVariablesJson(json: string): Record<string, unknown> | null {
  const trimmed = json.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Örnek değişkenler geçerli bir JSON nesnesi olmalıdır.");
  }
  return parsed as Record<string, unknown>;
}

export function formatMailTemplateTestEmailError(
  err: unknown,
  fallback: string,
  endpointNotFoundMessage: string,
): string {
  if (err instanceof ApiError) {
    if (err.status === 404 && err.message === "Not Found") {
      return endpointNotFoundMessage;
    }
    return err.message || fallback;
  }
  return fallback;
}

/** Keep manual subject override when the user has edited the field before preview. */
export function resolveSubjectAfterPreview(
  currentSubject: string,
  renderedSubject: string,
  subjectTouched: boolean,
): string {
  return subjectTouched ? currentSubject : renderedSubject;
}
