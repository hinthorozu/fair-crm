import { buildApiHeaders, config } from "../config";
import { apiRequest, ApiError, fetchWithTimeout } from "./client";
import type { QuoteTemplate, QuoteTemplatePayload } from "../types/quoteTemplates";

const MANAGED_LOGO_PREFIX = "/api/v1/data/quote-template-logos/";

export const listQuoteTemplates = () => apiRequest<{ items: QuoteTemplate[] }>("/api/v1/quote-templates");
export const createQuoteTemplate = (payload: QuoteTemplatePayload) => apiRequest<QuoteTemplate>("/api/v1/quote-templates", { method: "POST", body: JSON.stringify(payload) });
export const updateQuoteTemplate = (id: string, payload: QuoteTemplatePayload) => apiRequest<QuoteTemplate>(`/api/v1/quote-templates/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const uploadQuoteTemplateLogo = (file: File) => {
  const form = new FormData(); form.append("file", file);
  return apiRequest<{ url: string }>("/api/v1/quote-templates/logo", { method: "POST", body: form });
};

export function isManagedQuoteTemplateLogoUrl(url: string): boolean {
  return url.startsWith(MANAGED_LOGO_PREFIX);
}

export async function fetchManagedQuoteTemplateLogo(url: string): Promise<Blob> {
  if (!isManagedQuoteTemplateLogoUrl(url)) {
    throw new ApiError("Yönetilmeyen logo URL'si güvenli asset fetch ile alınamaz.", 400);
  }
  const response = await fetchWithTimeout(
    `${config.apiBaseUrl}${url}`,
    { headers: buildApiHeaders({}) },
  );
  if (!response.ok) {
    const text = await response.text();
    let detail = `HTTP ${response.status}`;
    try {
      const data = JSON.parse(text) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      if (text) detail = text;
    }
    throw new ApiError(detail, response.status);
  }
  return response.blob();
}
