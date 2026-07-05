import React from "react";
import {
  createMailTemplate,
  deleteMailTemplate,
  listMailTemplates,
  renderMailTemplate,
  updateMailTemplate,
  ApiError,
} from "../api/mailTemplates";
import { listSmtpAccounts } from "../api/smtp";
import { MailTemplateActionsMenu } from "../components/mail_templates/MailTemplateActionsMenu";
import { MailTemplateForm } from "../components/mail_templates/MailTemplateForm";
import { MailTemplatePreviewPanel } from "../components/mail_templates/MailTemplatePreviewPanel";
import { MailTemplateTestEmailPanel } from "../components/mail_templates/MailTemplateTestEmailPanel";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  canPerformMailTemplateAction,
  canSetDefaultMailTemplate,
  getGrantedMailTemplatePermissions,
} from "../permissions/mailTemplatePermissions";
import type { MailTemplate, MailTemplateType, RenderMailTemplateResponse } from "../types/mailTemplates";
import type { SmtpAccount } from "../types/smtp";
import { DEFAULT_RENDER_VARIABLES_JSON, MAIL_TEMPLATE_TYPES } from "../utils/mailTemplateForm";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

type ActiveFilter = "all" | "active" | "inactive";
type DefaultFilter = "all" | "default" | "non-default";

export function MailTemplatesPage() {
  const grantedPermissions = React.useMemo(() => getGrantedMailTemplatePermissions(), []);
  const canRead = canPerformMailTemplateAction(grantedPermissions, "read");
  const canCreate = canPerformMailTemplateAction(grantedPermissions, "create");
  const canUpdate = canPerformMailTemplateAction(grantedPermissions, "update");
  const canDelete = canPerformMailTemplateAction(grantedPermissions, "delete");
  const canRender = canPerformMailTemplateAction(grantedPermissions, "render");
  const canTestSend = canPerformMailTemplateAction(grantedPermissions, "test_send");

  const [templates, setTemplates] = React.useState<MailTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<MailTemplate | null>(null);
  const [formSaving, setFormSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<MailTemplate | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = React.useState<MailTemplate | null>(null);
  const [previewVariablesJson, setPreviewVariablesJson] = React.useState(DEFAULT_RENDER_VARIABLES_JSON);
  const [previewRendering, setPreviewRendering] = React.useState(false);
  const [previewError, setPreviewError] = React.useState<string | null>(null);
  const [previewResult, setPreviewResult] = React.useState<RenderMailTemplateResponse | null>(null);
  const [setDefaultTarget, setSetDefaultTarget] = React.useState<MailTemplate | null>(null);
  const [settingDefaultId, setSettingDefaultId] = React.useState<string | null>(null);
  const [testEmailTarget, setTestEmailTarget] = React.useState<MailTemplate | null>(null);
  const [smtpAccounts, setSmtpAccounts] = React.useState<SmtpAccount[]>([]);

  const [filterType, setFilterType] = React.useState<MailTemplateType | "all">("all");
  const [filterLanguage, setFilterLanguage] = React.useState<string>("all");
  const [filterActive, setFilterActive] = React.useState<ActiveFilter>("all");
  const [filterDefault, setFilterDefault] = React.useState<DefaultFilter>("all");

  const loadTemplates = React.useCallback(async () => {
    if (!canRead) {
      setTemplates([]);
      setLoading(false);
      setError(adminLabels.mailTemplatesPermissionDenied);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await listMailTemplates();
      setTemplates(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesLoadError);
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  React.useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  const languageOptions = React.useMemo(() => {
    const langs = new Set(templates.map((item) => item.language));
    return Array.from(langs).sort();
  }, [templates]);

  const filteredTemplates = React.useMemo(() => {
    return templates.filter((item) => {
      if (filterType !== "all" && item.template_type !== filterType) return false;
      if (filterLanguage !== "all" && item.language !== filterLanguage) return false;
      if (filterActive === "active" && !item.is_active) return false;
      if (filterActive === "inactive" && item.is_active) return false;
      if (filterDefault === "default" && !item.is_default) return false;
      if (filterDefault === "non-default" && item.is_default) return false;
      return true;
    });
  }, [templates, filterType, filterLanguage, filterActive, filterDefault]);

  const openCreate = () => {
    setEditing(null);
    setFormError(null);
    setModal("create");
  };

  const openEdit = (template: MailTemplate) => {
    setEditing(template);
    setFormError(null);
    setModal("edit");
  };

  const closeModal = React.useCallback(() => {
    setModal(null);
    setEditing(null);
    setFormError(null);
  }, []);

  const openPreview = (template: MailTemplate) => {
    setPreviewTarget(template);
    setPreviewVariablesJson(DEFAULT_RENDER_VARIABLES_JSON);
    setPreviewError(null);
    setPreviewResult(null);
  };

  const closePreview = () => {
    setPreviewTarget(null);
    setPreviewError(null);
    setPreviewResult(null);
  };

  const handleCreate = async (payload: Parameters<typeof createMailTemplate>[0]) => {
    setFormSaving(true);
    setFormError(null);
    try {
      await createMailTemplate(payload);
      closeModal();
      setSuccess(adminLabels.mailTemplatesCreateSuccess);
      await loadTemplates();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesCreateError);
    } finally {
      setFormSaving(false);
    }
  };

  const handleUpdate = async (payload: Parameters<typeof updateMailTemplate>[1]) => {
    if (!editing) return;
    setFormSaving(true);
    setFormError(null);
    try {
      await updateMailTemplate(editing.id, payload);
      closeModal();
      setSuccess(adminLabels.mailTemplatesUpdateSuccess);
      await loadTemplates();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesUpdateError);
    } finally {
      setFormSaving(false);
    }
  };

  const handleDelete = async (template: MailTemplate) => {
    setDeletingId(template.id);
    setError(null);
    try {
      await deleteMailTemplate(template.id);
      setDeleteTarget(null);
      setSuccess(adminLabels.mailTemplatesDeleteSuccess);
      await loadTemplates();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesDeleteError);
    } finally {
      setDeletingId(null);
    }
  };

  const handleRenderPreview = async (variables: Record<string, unknown>) => {
    if (!previewTarget || !canRender) return;
    setPreviewRendering(true);
    setPreviewError(null);
    try {
      const result = await renderMailTemplate(previewTarget.id, { variables });
      setPreviewResult(result);
    } catch (err) {
      setPreviewError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesRenderError);
      setPreviewResult(null);
    } finally {
      setPreviewRendering(false);
    }
  };

  const openTestEmail = async (template: MailTemplate) => {
    setTestEmailTarget(template);
    try {
      const response = await listSmtpAccounts();
      setSmtpAccounts(response.items);
    } catch {
      setSmtpAccounts([]);
    }
  };

  const closeTestEmail = () => {
    setTestEmailTarget(null);
    setSmtpAccounts([]);
  };

  const handleSetDefault = async (template: MailTemplate) => {
    if (!canSetDefaultMailTemplate(template, grantedPermissions)) return;
    setSettingDefaultId(template.id);
    setError(null);
    try {
      await updateMailTemplate(template.id, { is_default: true });
      setSetDefaultTarget(null);
      setSuccess(adminLabels.mailTemplatesSetDefaultSuccess);
      await loadTemplates();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : adminLabels.mailTemplatesSetDefaultError);
    } finally {
      setSettingDefaultId(null);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<MailTemplate>[]>(
    () => [
      {
        key: "name",
        title: adminLabels.mailTemplatesColName,
        sortable: true,
        render: (template) => (
          <div className="mail-template-name-cell">
            <span>{template.name}</span>
            {template.is_default ? (
              <Badge variant="info">{adminLabels.mailTemplatesDefaultBadge}</Badge>
            ) : null}
          </div>
        ),
      },
      {
        key: "key",
        title: adminLabels.mailTemplatesColKey,
        sortable: true,
        render: (template) => template.key,
      },
      {
        key: "template_type",
        title: adminLabels.mailTemplatesColType,
        sortable: true,
        render: (template) => template.template_type,
      },
      {
        key: "language",
        title: adminLabels.mailTemplatesColLanguage,
        sortable: true,
        render: (template) => template.language,
      },
      {
        key: "is_active",
        title: adminLabels.mailTemplatesColActive,
        sortable: true,
        render: (template) =>
          template.is_active ? (
            <Badge variant="success">{adminLabels.mailTemplatesActiveBadge}</Badge>
          ) : (
            <Badge variant="neutral">{adminLabels.mailTemplatesInactiveBadge}</Badge>
          ),
      },
      {
        key: "is_default",
        title: adminLabels.mailTemplatesColDefault,
        sortable: true,
        render: (template) => (template.is_default ? adminLabels.mailTemplatesDefaultBadge : "—"),
      },
      {
        key: "updated_at",
        title: adminLabels.mailTemplatesColUpdatedAt,
        sortable: true,
        render: (template) => formatDateTime(template.updated_at),
      },
      {
        key: "actions",
        title: adminLabels.colActions,
        sortable: false,
        render: (template) => (
          <MailTemplateActionsMenu
            template={template}
            canEdit={canUpdate}
            canPreview={canRender}
            canTestSend={canTestSend}
            canSetDefault={canSetDefaultMailTemplate(template, grantedPermissions)}
            canDelete={canDelete}
            busy={deletingId === template.id || settingDefaultId === template.id}
            onEdit={canUpdate ? openEdit : undefined}
            onPreview={canRender ? openPreview : undefined}
            onTestEmail={canTestSend ? (item) => void openTestEmail(item) : undefined}
            onSetDefault={
              canSetDefaultMailTemplate(template, grantedPermissions)
                ? (item) => setSetDefaultTarget(item)
                : undefined
            }
            onDelete={canDelete ? (item) => setDeleteTarget(item) : undefined}
          />
        ),
      },
    ],
    [canDelete, canRender, canTestSend, canUpdate, deletingId, grantedPermissions, settingDefaultId],
  );

  return (
    <div className="page mail-templates-page">
      <PageHeader
        title={adminLabels.mailTemplatesTitle}
        subtitle={adminLabels.mailTemplatesSubtitle}
        actions={
          canCreate ? (
            <button type="button" className="btn primary" onClick={openCreate}>
              {adminLabels.mailTemplatesNew}
            </button>
          ) : null
        }
      />

      {success ? <div className="banner success">{success}</div> : null}
      {error ? <p className="form-error">{error}</p> : null}

      <div className="mail-template-filters">
        <label>
          {adminLabels.mailTemplatesFilterType}
          <select
            className="form-control"
            value={filterType}
            onChange={(event) => setFilterType(event.target.value as MailTemplateType | "all")}
          >
            <option value="all">{adminLabels.mailTemplatesFilterAll}</option>
            {MAIL_TEMPLATE_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <label>
          {adminLabels.mailTemplatesFilterLanguage}
          <select
            className="form-control"
            value={filterLanguage}
            onChange={(event) => setFilterLanguage(event.target.value)}
          >
            <option value="all">{adminLabels.mailTemplatesFilterAll}</option>
            {languageOptions.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </label>

        <label>
          {adminLabels.mailTemplatesFilterActive}
          <select
            className="form-control"
            value={filterActive}
            onChange={(event) => setFilterActive(event.target.value as ActiveFilter)}
          >
            <option value="all">{adminLabels.mailTemplatesFilterAll}</option>
            <option value="active">{adminLabels.mailTemplatesFilterActiveOnly}</option>
            <option value="inactive">{adminLabels.mailTemplatesFilterInactiveOnly}</option>
          </select>
        </label>

        <label>
          {adminLabels.mailTemplatesFilterDefault}
          <select
            className="form-control"
            value={filterDefault}
            onChange={(event) => setFilterDefault(event.target.value as DefaultFilter)}
          >
            <option value="all">{adminLabels.mailTemplatesFilterAll}</option>
            <option value="default">{adminLabels.mailTemplatesFilterDefaultOnly}</option>
            <option value="non-default">{adminLabels.mailTemplatesFilterNonDefault}</option>
          </select>
        </label>
      </div>

      <UniversalDataTable
        items={filteredTemplates}
        columns={columns}
        rowKey={(template) => template.id}
        loading={loading}
        error={error}
        onRetry={() => void loadTemplates()}
        emptyState={
          error ? undefined : (
            <EmptyState
              title={adminLabels.mailTemplatesEmptyTitle}
              description={adminLabels.mailTemplatesEmptyDescription}
              actionLabel={canCreate ? adminLabels.mailTemplatesNew : undefined}
              onAction={canCreate ? openCreate : undefined}
            />
          )
        }
      />

      {modal === "create" ? (
        <FormModal title={adminLabels.mailTemplatesNew} onClose={closeModal} size="lg">
          <MailTemplateForm
            mode="create"
            saving={formSaving}
            error={formError}
            onCancel={closeModal}
            onSubmitCreate={handleCreate}
            onSubmitUpdate={handleUpdate}
          />
        </FormModal>
      ) : null}

      {modal === "edit" && editing ? (
        <FormModal title={adminLabels.mailTemplatesEdit} onClose={closeModal} size="lg">
          <MailTemplateForm
            mode="edit"
            initial={editing}
            saving={formSaving}
            error={formError}
            onCancel={closeModal}
            onSubmitCreate={handleCreate}
            onSubmitUpdate={handleUpdate}
          />
        </FormModal>
      ) : null}

      {previewTarget ? (
        <Modal title={adminLabels.mailTemplatesPreview} onClose={closePreview} size="lg">
          <div className="crm-form">
            <p className="text-muted">
              {previewTarget.name} ({previewTarget.key})
            </p>
            <MailTemplatePreviewPanel
              variablesJson={previewVariablesJson}
              onVariablesJsonChange={setPreviewVariablesJson}
              rendering={previewRendering}
              error={previewError}
              result={previewResult}
              onRender={handleRenderPreview}
              canRender={canRender}
            />
          </div>
        </Modal>
      ) : null}

      {deleteTarget ? (
        <ConfirmDialog
          title={adminLabels.mailTemplatesDeleteTitle}
          message={adminLabels.mailTemplatesDeleteConfirm}
          confirmLabel={adminLabels.actionDelete}
          variant="danger"
          loading={deletingId === deleteTarget.id}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete(deleteTarget)}
        />
      ) : null}

      {setDefaultTarget ? (
        <ConfirmDialog
          title={adminLabels.mailTemplatesSetDefaultTitle}
          message={adminLabels.mailTemplatesSetDefaultConfirm}
          confirmLabel={adminLabels.mailTemplatesActionSetDefault}
          loading={settingDefaultId === setDefaultTarget.id}
          onCancel={() => setSetDefaultTarget(null)}
          onConfirm={() => void handleSetDefault(setDefaultTarget)}
        />
      ) : null}

      {testEmailTarget ? (
        <FormModal title={adminLabels.mailTemplatesTestEmailTitle} onClose={closeTestEmail} size="lg">
          <MailTemplateTestEmailPanel
            template={testEmailTarget}
            smtpAccounts={smtpAccounts}
            canRender={canRender}
            canTestSend={canTestSend}
            onCancel={closeTestEmail}
          />
        </FormModal>
      ) : null}
    </div>
  );
}
