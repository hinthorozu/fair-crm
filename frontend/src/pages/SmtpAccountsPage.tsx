import React from "react";
import {
  createEmailAccount,
  deleteEmailAccount,
  listEmailAccounts,
  sendTestEmailAccountMail,
  setDefaultEmailAccount,
  updateEmailAccount,
  ApiError,
} from "../api/emailAccounts";
import { EmailAccountForm, resolveEmailAccountType } from "../components/smtp/EmailAccountForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { TableRowActions } from "../components/ui/TableRowActions";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  canPerformEmailAccountAction,
  canSetDefaultEmailAccount,
  getGrantedPermissions,
} from "../permissions/emailAccountPermissions";
import type { EmailAccount, EmailAccountType, UpdateEmailAccountPayload } from "../types/smtp";
import {
  clearIdIfMatches,
  shouldApplyAccountScopedResult,
} from "../utils/emailAccountAsyncIsolation";
import {
  responseContainsPassword,
  emailAccountPasswordSet,
  formatSmtpTestMailError,
} from "../utils/emailAccountForm";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function encryptionLabel(value: EmailAccount["encryption_type"]): string {
  return value.toUpperCase();
}

function accountTypeLabel(accountType: EmailAccountType): string {
  return accountType === "provider"
    ? adminLabels.smtpAccountTypeProvider
    : adminLabels.smtpAccountTypeSmtp;
}

export function SmtpAccountsPage() {
  const grantedPermissions = React.useMemo(() => getGrantedPermissions(), []);
  const canRead = canPerformEmailAccountAction(grantedPermissions, "read");
  const canCreate = canPerformEmailAccountAction(grantedPermissions, "create");
  const canUpdate = canPerformEmailAccountAction(grantedPermissions, "update");
  const canDelete = canPerformEmailAccountAction(grantedPermissions, "delete");

  const [accounts, setAccounts] = React.useState<EmailAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<EmailAccount | null>(null);
  const [formSaving, setFormSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [testMailRunning, setTestMailRunning] = React.useState(false);
  const [testMailError, setTestMailError] = React.useState<string | null>(null);
  const [testMailSuccess, setTestMailSuccess] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [settingDefaultId, setSettingDefaultId] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<EmailAccount | null>(null);
  const [deactivateConfirmPayload, setDeactivateConfirmPayload] =
    React.useState<UpdateEmailAccountPayload | null>(null);

  const editingRef = React.useRef<EmailAccount | null>(null);
  const modalRef = React.useRef<"create" | "edit" | null>(null);
  const testMailAbortRef = React.useRef<AbortController | null>(null);
  const testMailRequestIdRef = React.useRef(0);
  const testMailAccountIdRef = React.useRef<string | null>(null);
  const formRequestIdRef = React.useRef(0);
  const formTargetIdRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    editingRef.current = editing;
  }, [editing]);

  React.useEffect(() => {
    modalRef.current = modal;
  }, [modal]);

  const invalidateTestMail = React.useCallback(() => {
    testMailAbortRef.current?.abort();
    testMailAbortRef.current = null;
    testMailRequestIdRef.current += 1;
    testMailAccountIdRef.current = null;
    setTestMailRunning(false);
    setTestMailError(null);
    setTestMailSuccess(null);
  }, []);

  const invalidateFormOp = React.useCallback(() => {
    formRequestIdRef.current += 1;
    formTargetIdRef.current = null;
    setFormSaving(false);
    setFormError(null);
  }, []);

  const loadAccounts = React.useCallback(async () => {
    if (!canRead) {
      setAccounts([]);
      setLoading(false);
      setError(adminLabels.smtpPermissionDenied);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await listEmailAccounts();
      if (response.items.some((item) => responseContainsPassword(item))) {
        throw new Error(adminLabels.smtpUnexpectedPasswordField);
      }
      setAccounts(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.smtpLoadError);
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  React.useEffect(() => {
    void loadAccounts();
  }, [loadAccounts]);

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  React.useEffect(() => {
    return () => {
      testMailAbortRef.current?.abort();
    };
  }, []);

  const openCreate = () => {
    invalidateTestMail();
    invalidateFormOp();
    setEditing(null);
    setModal("create");
  };

  const openEdit = (account: EmailAccount) => {
    invalidateTestMail();
    invalidateFormOp();
    setEditing(account);
    setModal("edit");
  };

  const closeModal = React.useCallback(() => {
    invalidateTestMail();
    invalidateFormOp();
    setDeactivateConfirmPayload(null);
    setModal(null);
    setEditing(null);
  }, [invalidateFormOp, invalidateTestMail]);

  const handleCreate = async (payload: Parameters<typeof createEmailAccount>[0]) => {
    const requestId = ++formRequestIdRef.current;
    formTargetIdRef.current = "__create__";
    setFormSaving(true);
    setFormError(null);
    try {
      await createEmailAccount(payload);
      if (
        requestId !== formRequestIdRef.current ||
        formTargetIdRef.current !== "__create__" ||
        modalRef.current !== "create"
      ) {
        return;
      }
      closeModal();
      setSuccess(adminLabels.smtpCreateSuccess);
      await loadAccounts();
    } catch (err) {
      if (
        requestId !== formRequestIdRef.current ||
        formTargetIdRef.current !== "__create__" ||
        modalRef.current !== "create"
      ) {
        return;
      }
      setFormError(err instanceof ApiError ? err.message : adminLabels.smtpCreateError);
    } finally {
      if (requestId === formRequestIdRef.current && formTargetIdRef.current === "__create__") {
        setFormSaving(false);
      }
    }
  };

  const performUpdate = async (payload: UpdateEmailAccountPayload) => {
    const accountId = editingRef.current?.id;
    if (!accountId) return;
    const requestId = ++formRequestIdRef.current;
    formTargetIdRef.current = accountId;
    setFormSaving(true);
    setFormError(null);
    try {
      await updateEmailAccount(accountId, payload);
      if (
        !shouldApplyAccountScopedResult({
          requestId,
          activeRequestId: formRequestIdRef.current,
          operationAccountId: accountId,
          activeOperationAccountId: formTargetIdRef.current,
          modalAccountId: modalRef.current === "edit" ? editingRef.current?.id ?? null : null,
        })
      ) {
        return;
      }
      setDeactivateConfirmPayload(null);
      closeModal();
      setSuccess(adminLabels.smtpUpdateSuccess);
      await loadAccounts();
    } catch (err) {
      if (
        !shouldApplyAccountScopedResult({
          requestId,
          activeRequestId: formRequestIdRef.current,
          operationAccountId: accountId,
          activeOperationAccountId: formTargetIdRef.current,
          modalAccountId: modalRef.current === "edit" ? editingRef.current?.id ?? null : null,
        })
      ) {
        return;
      }
      setFormError(err instanceof ApiError ? err.message : adminLabels.smtpUpdateError);
    } finally {
      if (requestId === formRequestIdRef.current && formTargetIdRef.current === accountId) {
        setFormSaving(false);
      }
    }
  };

  const handleUpdate = async (payload: Parameters<typeof updateEmailAccount>[1]) => {
    if (editingRef.current?.is_default && payload.is_active === false) {
      setDeactivateConfirmPayload(payload);
      return;
    }
    await performUpdate(payload);
  };

  const handleSetDefault = async (account: EmailAccount) => {
    if (!canSetDefaultEmailAccount(account, grantedPermissions)) {
      return;
    }
    const accountId = account.id;
    setSettingDefaultId(accountId);
    setError(null);
    try {
      await setDefaultEmailAccount(accountId);
      setSuccess(adminLabels.smtpSetDefaultSuccess);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.smtpSetDefaultError);
    } finally {
      setSettingDefaultId((current) => clearIdIfMatches(current, accountId));
    }
  };

  const handleTestMail = async (recipient: string) => {
    const accountId = editingRef.current?.id;
    if (!accountId || !canUpdate || modalRef.current !== "edit") return;

    testMailAbortRef.current?.abort();
    const controller = new AbortController();
    testMailAbortRef.current = controller;
    const requestId = ++testMailRequestIdRef.current;
    testMailAccountIdRef.current = accountId;

    setTestMailRunning(true);
    setTestMailError(null);
    setTestMailSuccess(null);

    try {
      const result = await sendTestEmailAccountMail(
        accountId,
        { recipient },
        { signal: controller.signal },
      );
      if (
        !shouldApplyAccountScopedResult({
          requestId,
          activeRequestId: testMailRequestIdRef.current,
          operationAccountId: accountId,
          activeOperationAccountId: testMailAccountIdRef.current,
          modalAccountId: modalRef.current === "edit" ? editingRef.current?.id ?? null : null,
        })
      ) {
        return;
      }
      setTestMailSuccess(result.message || adminLabels.smtpTestMailSuccess);
    } catch (err) {
      if (controller.signal.aborted) return;
      if (
        !shouldApplyAccountScopedResult({
          requestId,
          activeRequestId: testMailRequestIdRef.current,
          operationAccountId: accountId,
          activeOperationAccountId: testMailAccountIdRef.current,
          modalAccountId: modalRef.current === "edit" ? editingRef.current?.id ?? null : null,
        })
      ) {
        return;
      }
      const rawMessage = err instanceof ApiError ? err.message : adminLabels.smtpTestMailError;
      setTestMailError(formatSmtpTestMailError(rawMessage));
    } finally {
      if (
        requestId === testMailRequestIdRef.current &&
        testMailAccountIdRef.current === accountId
      ) {
        setTestMailRunning(false);
      }
    }
  };

  const handleDelete = async (account: EmailAccount) => {
    const accountId = account.id;
    setDeletingId(accountId);
    setError(null);
    try {
      await deleteEmailAccount(accountId);
      setDeleteTarget((current) => (current?.id === accountId ? null : current));
      setSuccess(adminLabels.smtpDeleteSuccess);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.smtpDeleteError);
    } finally {
      setDeletingId((current) => clearIdIfMatches(current, accountId));
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<EmailAccount>[]>(
    () => [
      {
        key: "name",
        title: adminLabels.smtpColName,
        sortable: true,
        render: (account) => (
          <div className="smtp-name-cell">
            <span>{account.name}</span>
            {account.is_default ? <Badge variant="info">{adminLabels.smtpDefaultBadge}</Badge> : null}
          </div>
        ),
      },
      {
        key: "account_type",
        title: adminLabels.smtpColAccountType,
        sortable: true,
        render: (account) => (
          <Badge variant="neutral">{accountTypeLabel(resolveEmailAccountType(account))}</Badge>
        ),
      },
      {
        key: "from_name",
        title: adminLabels.smtpColFromName,
        sortable: true,
        render: (account) => account.from_name || "—",
      },
      {
        key: "from_email",
        title: adminLabels.smtpColFromEmail,
        sortable: true,
        render: (account) => account.from_email,
      },
      {
        key: "host",
        title: adminLabels.smtpColHost,
        sortable: true,
        render: (account) =>
          resolveEmailAccountType(account) === "smtp" ? account.host : "—",
      },
      {
        key: "port",
        title: adminLabels.smtpColPort,
        sortable: true,
        render: (account) =>
          resolveEmailAccountType(account) === "smtp" ? account.port : "—",
      },
      {
        key: "encryption_type",
        title: adminLabels.smtpColEncryption,
        sortable: true,
        render: (account) =>
          resolveEmailAccountType(account) === "smtp"
            ? encryptionLabel(account.encryption_type)
            : "—",
      },
      {
        key: "is_active",
        title: adminLabels.smtpColActive,
        sortable: true,
        render: (account) =>
          account.is_active ? (
            <Badge variant="success">{adminLabels.smtpActiveBadge}</Badge>
          ) : (
            <Badge variant="neutral">{adminLabels.smtpInactiveBadge}</Badge>
          ),
      },
      {
        key: "password_set",
        title: adminLabels.smtpColHasPassword,
        sortable: true,
        render: (account) =>
          resolveEmailAccountType(account) === "smtp"
            ? emailAccountPasswordSet(account)
              ? adminLabels.smtpPasswordConfigured
              : adminLabels.smtpPasswordMissing
            : "—",
      },
      {
        key: "updated_at",
        title: adminLabels.smtpColUpdatedAt,
        sortable: true,
        render: (account) => formatDateTime(account.updated_at),
      },
      {
        key: "actions",
        title: adminLabels.colActions,
        sortable: false,
        render: (account) => (
          <TableRowActions className="smtp-list-actions">
            {canUpdate ? (
              <button type="button" className="btn btn-sm secondary" onClick={() => openEdit(account)}>
                {adminLabels.smtpActionEdit}
              </button>
            ) : null}
            {canUpdate ? (
              <button
                type="button"
                className="btn btn-sm secondary"
                disabled={
                  !canSetDefaultEmailAccount(account, grantedPermissions) ||
                  settingDefaultId === account.id
                }
                title={
                  !account.is_active
                    ? adminLabels.smtpSetDefaultInactiveHint
                    : account.is_default
                      ? adminLabels.smtpAlreadyDefaultHint
                      : undefined
                }
                onClick={() => void handleSetDefault(account)}
              >
                {adminLabels.smtpActionSetDefault}
              </button>
            ) : null}
            {canDelete ? (
              <button
                type="button"
                className="btn btn-sm danger"
                disabled={deletingId === account.id}
                onClick={() => setDeleteTarget(account)}
              >
                {adminLabels.actionDelete}
              </button>
            ) : null}
          </TableRowActions>
        ),
      },
    ],
    [canDelete, canUpdate, deletingId, grantedPermissions, settingDefaultId],
  );

  return (
    <PageShell className="smtp-accounts-page email-accounts-page">
      <PageHeader
        title={adminLabels.smtpTitle}
        subtitle={adminLabels.smtpSubtitle}
        actions={
          canCreate ? (
            <button type="button" className="btn primary" onClick={openCreate}>
              {adminLabels.smtpNewAccount}
            </button>
          ) : null
        }
      />

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <UniversalDataTable
        items={accounts}
        columns={columns}
        rowKey={(account) => account.id}
        loading={loading}
        error={error}
        onRetry={() => void loadAccounts()}
        emptyState={
          error ? undefined : (
            <EmptyState
              title={adminLabels.smtpEmptyTitle}
              description={adminLabels.smtpEmptyDescription}
              actionLabel={canCreate ? adminLabels.smtpNewAccount : undefined}
              onAction={canCreate ? openCreate : undefined}
            />
          )
        }
      />

      {modal === "create" ? (
        <FormModal title={adminLabels.smtpCreateModalTitle} onClose={closeModal}>
          <EmailAccountForm
            key="create"
            mode="create"
            saving={formSaving}
            error={formError}
            testError={null}
            testSuccess={null}
            onCancel={closeModal}
            onSubmitCreate={handleCreate}
            onSubmitUpdate={handleUpdate}
          />
        </FormModal>
      ) : null}

      {modal === "edit" && editing ? (
        <FormModal title={adminLabels.smtpEditAccount} onClose={closeModal}>
          <EmailAccountForm
            key={editing.id}
            mode="edit"
            initial={editing}
            saving={formSaving}
            testing={testMailRunning}
            error={formError}
            testError={testMailError}
            testSuccess={testMailSuccess}
            onCancel={closeModal}
            onSubmitCreate={handleCreate}
            onSubmitUpdate={handleUpdate}
            onTestMail={canUpdate ? handleTestMail : undefined}
          />
        </FormModal>
      ) : null}

      {deleteTarget ? (
        <ConfirmDialog
          title={adminLabels.smtpDeleteTitle}
          message={
            deleteTarget.is_default
              ? adminLabels.smtpDeleteDefaultConfirm.replace("{name}", deleteTarget.name)
              : adminLabels.smtpDeleteConfirm.replace("{name}", deleteTarget.name)
          }
          confirmLabel={adminLabels.actionDelete}
          variant="danger"
          loading={deletingId === deleteTarget.id}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete(deleteTarget)}
        />
      ) : null}

      {deactivateConfirmPayload ? (
        <ConfirmDialog
          title={adminLabels.smtpDeactivateDefaultTitle}
          message={adminLabels.smtpDeactivateDefaultConfirm}
          confirmLabel={adminLabels.smtpDeactivateDefaultConfirmLabel}
          variant="danger"
          loading={formSaving}
          onCancel={() => setDeactivateConfirmPayload(null)}
          onConfirm={() => void performUpdate(deactivateConfirmPayload)}
        />
      ) : null}
    </PageShell>
  );
}
