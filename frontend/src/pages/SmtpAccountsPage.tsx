import React from "react";
import {
  createSmtpAccount,
  deleteSmtpAccount,
  listSmtpAccounts,
  sendTestSmtpMail,
  setDefaultSmtpAccount,
  updateSmtpAccount,
  ApiError,
} from "../api/smtp";
import { SmtpAccountForm } from "../components/smtp/SmtpAccountForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { TableRowActions } from "../components/ui/TableRowActions";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  canPerformSmtpAction,
  canSetDefaultSmtpAccount,
  getGrantedPermissions,
} from "../permissions/smtpPermissions";
import type { SmtpAccount } from "../types/smtp";
import { responseContainsPassword, smtpPasswordSet, formatSmtpTestMailError } from "../utils/smtpForm";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function encryptionLabel(value: SmtpAccount["encryption_type"]): string {
  return value.toUpperCase();
}

export function SmtpAccountsPage() {
  const grantedPermissions = React.useMemo(() => getGrantedPermissions(), []);
  const canRead = canPerformSmtpAction(grantedPermissions, "read");
  const canCreate = canPerformSmtpAction(grantedPermissions, "create");
  const canUpdate = canPerformSmtpAction(grantedPermissions, "update");
  const canDelete = canPerformSmtpAction(grantedPermissions, "delete");

  const [accounts, setAccounts] = React.useState<SmtpAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<SmtpAccount | null>(null);
  const [formSaving, setFormSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [testMailRunning, setTestMailRunning] = React.useState(false);
  const [testMailError, setTestMailError] = React.useState<string | null>(null);
  const [testMailSuccess, setTestMailSuccess] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [settingDefaultId, setSettingDefaultId] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<SmtpAccount | null>(null);

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
      const response = await listSmtpAccounts();
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

  const openCreate = () => {
    setEditing(null);
    setFormError(null);
    setModal("create");
  };

  const openEdit = (account: SmtpAccount) => {
    setEditing(account);
    setFormError(null);
    setTestMailError(null);
    setTestMailSuccess(null);
    setModal("edit");
  };

  const closeModal = React.useCallback(() => {
    setModal(null);
    setEditing(null);
    setFormError(null);
    setTestMailError(null);
    setTestMailSuccess(null);
  }, []);

  const handleCreate = async (payload: Parameters<typeof createSmtpAccount>[0]) => {
    setFormSaving(true);
    setFormError(null);
    try {
      await createSmtpAccount(payload);
      closeModal();
      setSuccess(adminLabels.smtpCreateSuccess);
      await loadAccounts();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : adminLabels.smtpCreateError);
    } finally {
      setFormSaving(false);
    }
  };

  const handleUpdate = async (payload: Parameters<typeof updateSmtpAccount>[1]) => {
    if (!editing) return;
    setFormSaving(true);
    setFormError(null);
    try {
      await updateSmtpAccount(editing.id, payload);
      closeModal();
      setSuccess(adminLabels.smtpUpdateSuccess);
      await loadAccounts();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : adminLabels.smtpUpdateError);
    } finally {
      setFormSaving(false);
    }
  };

  const handleSetDefault = async (account: SmtpAccount) => {
    if (!canSetDefaultSmtpAccount(account, grantedPermissions)) {
      return;
    }
    setSettingDefaultId(account.id);
    setError(null);
    try {
      await setDefaultSmtpAccount(account.id);
      setSuccess(adminLabels.smtpSetDefaultSuccess);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.smtpSetDefaultError);
    } finally {
      setSettingDefaultId(null);
    }
  };

  const handleTestMail = async (recipient: string) => {
    if (!editing || !canUpdate) return;
    setTestMailRunning(true);
    setTestMailError(null);
    setTestMailSuccess(null);
    try {
      const result = await sendTestSmtpMail(editing.id, { recipient });
      setTestMailSuccess(result.message || adminLabels.smtpTestMailSuccess);
    } catch (err) {
      const rawMessage = err instanceof ApiError ? err.message : adminLabels.smtpTestMailError;
      setTestMailError(formatSmtpTestMailError(rawMessage));
    } finally {
      setTestMailRunning(false);
    }
  };

  const handleDelete = async (account: SmtpAccount) => {
    setDeletingId(account.id);
    setError(null);
    try {
      await deleteSmtpAccount(account.id);
      setDeleteTarget(null);
      setSuccess(adminLabels.smtpDeleteSuccess);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.smtpDeleteError);
    } finally {
      setDeletingId(null);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<SmtpAccount>[]>(
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
        render: (account) => account.host,
      },
      {
        key: "port",
        title: adminLabels.smtpColPort,
        sortable: true,
        render: (account) => account.port,
      },
      {
        key: "encryption_type",
        title: adminLabels.smtpColEncryption,
        sortable: true,
        render: (account) => encryptionLabel(account.encryption_type),
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
          smtpPasswordSet(account)
            ? adminLabels.smtpPasswordConfigured
            : adminLabels.smtpPasswordMissing,
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
                  !canSetDefaultSmtpAccount(account, grantedPermissions) ||
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
    <PageShell className="smtp-accounts-page">
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
        <FormModal title={adminLabels.smtpNewAccount} onClose={closeModal}>
          <SmtpAccountForm
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
          <SmtpAccountForm
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
          message={adminLabels.smtpDeleteConfirm.replace("{name}", deleteTarget.name)}
          confirmLabel={adminLabels.actionDelete}
          variant="danger"
          loading={deletingId === deleteTarget.id}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete(deleteTarget)}
        />
      ) : null}
    </PageShell>
  );
}
