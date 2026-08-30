import { apiRequest, ApiError } from "./client";
import {
  EMAIL_ACCOUNTS_PERMISSION_READ,
  getGrantedPermissions,
  hasPermission,
} from "../permissions/emailAccountPermissions";
import type {
  CreateEmailAccountPayload,
  EmailAccount,
  EmailAccountListResponse,
  EmailAccountProviderListResponse,
  UpdateEmailAccountPayload,
  SendTestEmailAccountPayload,
  SendTestEmailAccountResponse,
} from "../types/smtp";

export { ApiError };

const EMAIL_ACCOUNTS_BASE = "/api/v1/email-accounts";
const EMAIL_ACCOUNTS_READ_DENIED =
  "E-posta hesaplarını görüntüleme yetkiniz yok (fair_crm.email_accounts.read).";

export async function listEmailAccounts(): Promise<EmailAccountListResponse> {
  if (!hasPermission(getGrantedPermissions(), EMAIL_ACCOUNTS_PERMISSION_READ)) {
    throw new ApiError(EMAIL_ACCOUNTS_READ_DENIED, 403);
  }
  return apiRequest<EmailAccountListResponse>(EMAIL_ACCOUNTS_BASE);
}

export async function listEmailAccountProviders(): Promise<EmailAccountProviderListResponse> {
  return apiRequest<EmailAccountProviderListResponse>(`${EMAIL_ACCOUNTS_BASE}/providers`);
}

export function createEmailAccount(payload: CreateEmailAccountPayload): Promise<EmailAccount> {
  return apiRequest<EmailAccount>(EMAIL_ACCOUNTS_BASE, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateEmailAccount(
  accountId: string,
  payload: UpdateEmailAccountPayload,
): Promise<EmailAccount> {
  return apiRequest<EmailAccount>(`${EMAIL_ACCOUNTS_BASE}/${encodeURIComponent(accountId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteEmailAccount(accountId: string): Promise<EmailAccount> {
  return apiRequest<EmailAccount>(`${EMAIL_ACCOUNTS_BASE}/${encodeURIComponent(accountId)}`, {
    method: "DELETE",
  });
}

export function setDefaultEmailAccount(accountId: string): Promise<EmailAccount> {
  return apiRequest<EmailAccount>(
    `${EMAIL_ACCOUNTS_BASE}/${encodeURIComponent(accountId)}/set-default`,
    { method: "POST" },
  );
}

export function sendTestEmailAccountMail(
  accountId: string,
  payload: SendTestEmailAccountPayload,
  options: { signal?: AbortSignal } = {},
): Promise<SendTestEmailAccountResponse> {
  return apiRequest<SendTestEmailAccountResponse>(
    `${EMAIL_ACCOUNTS_BASE}/${encodeURIComponent(accountId)}/test`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      signal: options.signal,
    },
  );
}
