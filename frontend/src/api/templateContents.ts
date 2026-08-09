import { apiRequest } from "./client";
import type { TemplateContent, TemplateContentTag } from "../types/templateContents";

export const listTemplateContentTags = () => apiRequest<{items: TemplateContentTag[]}>("/api/v1/template-content-tags");
export const createTemplateContentTag = (name: string) => apiRequest<TemplateContentTag>("/api/v1/template-content-tags", {method: "POST", body: JSON.stringify({name})});
export const updateTemplateContentTag = (id: string, name: string) => apiRequest<TemplateContentTag>(`/api/v1/template-content-tags/${id}`, {method: "PATCH", body: JSON.stringify({name})});
export const deleteTemplateContentTag = (id: string) => apiRequest<void>(`/api/v1/template-content-tags/${id}`, {method: "DELETE"});
export const listTemplateContents = () => apiRequest<{items: TemplateContent[]}>("/api/v1/template-contents");
export const createTemplateContent = (payload: {tag_id: string; title: string}) => apiRequest<TemplateContent>("/api/v1/template-contents", {method: "POST", body: JSON.stringify(payload)});
export const updateTemplateContent = (id: string, payload: {tag_id: string; title: string}) => apiRequest<TemplateContent>(`/api/v1/template-contents/${id}`, {method: "PATCH", body: JSON.stringify(payload)});
export const deleteTemplateContent = (id: string) => apiRequest<void>(`/api/v1/template-contents/${id}`, {method: "DELETE"});
