import { apiRequest } from "./client";
import type { QuoteTemplate, QuoteTemplatePayload } from "../types/quoteTemplates";

export const listQuoteTemplates = () => apiRequest<{ items: QuoteTemplate[] }>("/api/v1/quote-templates");
export const createQuoteTemplate = (payload: QuoteTemplatePayload) => apiRequest<QuoteTemplate>("/api/v1/quote-templates", { method: "POST", body: JSON.stringify(payload) });
export const updateQuoteTemplate = (id: string, payload: QuoteTemplatePayload) => apiRequest<QuoteTemplate>(`/api/v1/quote-templates/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const uploadQuoteTemplateLogo = (file: File) => {
  const form = new FormData(); form.append("file", file);
  return apiRequest<{ url: string }>("/api/v1/quote-templates/logo", { method: "POST", body: form });
};
