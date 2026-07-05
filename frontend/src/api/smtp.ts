import { apiRequest, ApiError } from "./client";
import type {
  CreateSmtpAccountPayload,
  SmtpAccount,
  SmtpAccountListResponse,
  UpdateSmtpAccountPayload,
  SendTestSmtpMailPayload,
  SendTestSmtpMailResponse,
} from "../types/smtp";

export { ApiError };

export async function listSmtpAccounts(): Promise<SmtpAccountListResponse> {
  return apiRequest<SmtpAccountListResponse>("/api/v1/smtp/accounts");
}

export function createSmtpAccount(payload: CreateSmtpAccountPayload): Promise<SmtpAccount> {
  return apiRequest<SmtpAccount>("/api/v1/smtp/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSmtpAccount(
  accountId: string,
  payload: UpdateSmtpAccountPayload,
): Promise<SmtpAccount> {
  return apiRequest<SmtpAccount>(`/api/v1/smtp/accounts/${encodeURIComponent(accountId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteSmtpAccount(accountId: string): Promise<SmtpAccount> {
  return apiRequest<SmtpAccount>(`/api/v1/smtp/accounts/${encodeURIComponent(accountId)}`, {
    method: "DELETE",
  });
}

export function setDefaultSmtpAccount(accountId: string): Promise<SmtpAccount> {
  return apiRequest<SmtpAccount>(
    `/api/v1/smtp/accounts/${encodeURIComponent(accountId)}/set-default`,
    { method: "POST" },
  );
}

export function sendTestSmtpMail(
  accountId: string,
  payload: SendTestSmtpMailPayload,
): Promise<SendTestSmtpMailResponse> {
  return apiRequest<SendTestSmtpMailResponse>(
    `/api/v1/smtp/accounts/${encodeURIComponent(accountId)}/test`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
