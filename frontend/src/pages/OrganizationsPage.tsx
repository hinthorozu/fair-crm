import React from "react";

import { ApiError } from "../api/client";
import {
  createOrganization,
  deleteOrganization,
  listOrganizations,
  updateOrganization,
  type Organization,
} from "../api/organizations";
import { useAuth } from "../auth/AuthContext";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormField, FormModal, TextInput, runAfterSuccessfulFormSubmit } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../components/ui/UniversalDataTable";
import { useModalFormCancel, useReportFormDirty } from "../hooks/useModalForm";
import { organizationLabels } from "../labels/organizationLabels";
import { hasGrantedCorePermission } from "../permissions/corePermissions";
import {
  PERMISSION_ORGANIZATIONS_SYSTEM,
  PERMISSION_ORGANIZATIONS_UPDATE,
} from "../permissions/navigationPermissions";

interface OrganizationFormProps {
  initialName: string;
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (name: string) => Promise<void>;
}

function OrganizationForm({ initialName, saving, error, onCancel, onSubmit }: OrganizationFormProps) {
  const [name, setName] = React.useState(initialName);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  useReportFormDirty({ name }, { name: initialName });
  const cancel = useModalFormCancel(onCancel);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setValidationError(organizationLabels.nameRequired);
      return;
    }
    setValidationError(null);
    await onSubmit(trimmedName);
  };

  return (
    <form id="organization-form" onSubmit={submit}>
      <FormField
        label={organizationLabels.organizationName}
        htmlFor="organization-name"
        required
        error={validationError ?? error ?? undefined}
        fullWidth
      >
        <TextInput
          id="organization-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          autoFocus
          disabled={saving}
          aria-invalid={Boolean(validationError || error)}
        />
      </FormField>
      <div className="form-actions">
        <button type="button" className="btn secondary" onClick={cancel} disabled={saving}>
          {organizationLabels.cancel}
        </button>
        <button type="submit" className="btn primary" disabled={saving}>
          {organizationLabels.save}
        </button>
      </div>
    </form>
  );
}

export function OrganizationsPage() {
  const { session } = useAuth();
  const [items, setItems] = React.useState<Organization[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<Organization | null | undefined>(undefined);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState<Organization | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);
  const grantedPermissions = session?.permissions ?? [];
  const canCreateOrganizations = session?.isSuperAdmin === true;
  const canUpdateOrganizations = hasGrantedCorePermission(
    grantedPermissions,
    PERMISSION_ORGANIZATIONS_UPDATE,
  );
  const canDeleteOrganizations = hasGrantedCorePermission(
    grantedPermissions,
    PERMISSION_ORGANIZATIONS_SYSTEM,
  );

  const load = React.useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      setItems(await listOrganizations());
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.message : organizationLabels.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const openCreate = React.useCallback(() => {
    if (!canCreateOrganizations) return;
    setEditing(null);
    setFormError(null);
  }, [canCreateOrganizations]);

  const openEdit = React.useCallback((organization: Organization) => {
    if (!canUpdateOrganizations) return;
    setEditing(organization);
    setFormError(null);
  }, [canUpdateOrganizations]);

  const closeForm = React.useCallback(() => {
    if (saving) return;
    setEditing(undefined);
    setFormError(null);
  }, [saving]);

  const saveOrganization = async (name: string) => {
    if (editing ? !canUpdateOrganizations : !canCreateOrganizations) return;
    setSaving(true);
    setFormError(null);
    try {
      if (editing) {
        await updateOrganization(editing.id, name);
      } else {
        await createOrganization(name);
      }
      runAfterSuccessfulFormSubmit(() => setEditing(undefined));
      await load();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : organizationLabels.saveError);
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!canDeleteOrganizations || !deleting) return;
    setDeleteBusy(true);
    try {
      await deleteOrganization(deleting.id);
      setDeleting(null);
      await load();
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.message : organizationLabels.deleteError);
      setDeleting(null);
    } finally {
      setDeleteBusy(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<Organization>[]>(
    () => [
      {
        key: "name",
        title: organizationLabels.organizationName,
        sortable: false,
        render: (organization) => organization.name,
      },
      ...(canUpdateOrganizations || canDeleteOrganizations
        ? [{
            key: "actions",
            title: organizationLabels.actions,
            sortable: false,
            className: "col-actions",
            render: (organization: Organization) => (
              <TableRowActions>
                {canUpdateOrganizations ? (
                  <button type="button" className="btn link" onClick={() => openEdit(organization)}>
                    {organizationLabels.edit}
                  </button>
                ) : null}
                {canDeleteOrganizations ? (
                  <button
                    type="button"
                    className="btn link danger"
                    onClick={() => setDeleting(organization)}
                  >
                    {organizationLabels.delete}
                  </button>
                ) : null}
              </TableRowActions>
            ),
          } as UniversalDataTableColumn<Organization>]
        : []),
    ],
    [canDeleteOrganizations, canUpdateOrganizations, openEdit],
  );

  const formOpen = editing !== undefined;

  return (
    <PageShell>
      <PageHeader
        title={organizationLabels.title}
        actions={
          canCreateOrganizations ? (
            <button type="button" className="btn primary" onClick={openCreate}>
              {organizationLabels.newOrganization}
            </button>
          ) : undefined
        }
      />

      <UniversalDataTable
        items={items}
        columns={columns}
        rowKey={(organization) => organization.id}
        loading={loading}
        error={loadError}
        onRetry={() => void load()}
        emptyState={
          <EmptyState
            title={organizationLabels.empty}
            actionLabel={canCreateOrganizations ? organizationLabels.newOrganization : undefined}
            onAction={canCreateOrganizations ? openCreate : undefined}
          />
        }
      />

      {formOpen && (
        <FormModal
          title={editing ? organizationLabels.editOrganization : organizationLabels.newOrganization}
          onClose={closeForm}
          formWidth="narrow"
        >
          <OrganizationForm
            key={editing?.id ?? "new-organization"}
            initialName={editing?.name ?? ""}
            saving={saving}
            error={formError}
            onCancel={closeForm}
            onSubmit={saveOrganization}
          />
        </FormModal>
      )}

      {deleting && canDeleteOrganizations && (
        <ConfirmDialog
          title={organizationLabels.deleteTitle}
          message={organizationLabels.deleteConfirm}
          confirmLabel={organizationLabels.delete}
          variant="danger"
          loading={deleteBusy}
          onCancel={() => setDeleting(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}
    </PageShell>
  );
}
