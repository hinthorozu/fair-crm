import { apiRequest, ApiError } from "./client";
import type {
  CreateMailTemplatePayload,
  MailTemplate,
  MailTemplateListResponse,
  RenderMailTemplatePayload,
  RenderMailTemplateResponse,
  SendTestMailTemplatePayload,
  SendTestMailTemplateResponse,
  UpdateMailTemplatePayload,
} from "../types/mailTemplates";

export { ApiError };

export async function listMailTemplates(): Promise<MailTemplateListResponse> {
  return apiRequest<MailTemplateListResponse>("/api/v1/mail-templates");
}

export function getMailTemplate(templateId: string): Promise<MailTemplate> {
  return apiRequest<MailTemplate>(`/api/v1/mail-templates/${encodeURIComponent(templateId)}`);
}

export function createMailTemplate(payload: CreateMailTemplatePayload): Promise<MailTemplate> {
  return apiRequest<MailTemplate>("/api/v1/mail-templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMailTemplate(
  templateId: string,
  payload: UpdateMailTemplatePayload,
): Promise<MailTemplate> {
  return apiRequest<MailTemplate>(`/api/v1/mail-templates/${encodeURIComponent(templateId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteMailTemplate(templateId: string): Promise<MailTemplate> {
  return apiRequest<MailTemplate>(`/api/v1/mail-templates/${encodeURIComponent(templateId)}`, {
    method: "DELETE",
  });
}

export function renderMailTemplate(
  templateId: string,
  payload: RenderMailTemplatePayload,
): Promise<RenderMailTemplateResponse> {
  return apiRequest<RenderMailTemplateResponse>(
    `/api/v1/mail-templates/${encodeURIComponent(templateId)}/render`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function sendTestMailTemplate(
  templateId: string,
  payload: SendTestMailTemplatePayload,
): Promise<SendTestMailTemplateResponse> {
  return apiRequest<SendTestMailTemplateResponse>(
    `/api/v1/mail-templates/${encodeURIComponent(templateId)}/test-email`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
