import React from "react";

import { ApiError } from "../api/client";
import {
  createOrganization,
  deleteOrganization,
  listOrganizations,
  updateOrganization,
  type Organization,
} from "../api/organizations";
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
  const [items, setItems] = React.useState<Organization[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<Organization | null | undefined>(undefined);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState<Organization | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

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
    setEditing(null);
    setFormError(null);
  }, []);

  const openEdit = React.useCallback((organization: Organization) => {
    setEditing(organization);
    setFormError(null);
  }, []);

  const closeForm = React.useCallback(() => {
    if (saving) return;
    setEditing(undefined);
    setFormError(null);
  }, [saving]);

  const saveOrganization = async (name: string) => {
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
    if (!deleting) return;
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
      {
        key: "actions",
        title: organizationLabels.actions,
        sortable: false,
        className: "col-actions",
        render: (organization) => (
          <TableRowActions>
            <button type="button" className="btn link" onClick={() => openEdit(organization)}>
              {organizationLabels.edit}
            </button>
            <button
              type="button"
              className="btn link danger"
              onClick={() => setDeleting(organization)}
            >
              {organizationLabels.delete}
            </button>
          </TableRowActions>
        ),
      },
    ],
    [openEdit],
  );

  const formOpen = editing !== undefined;

  return (
    <PageShell>
      <PageHeader
        title={organizationLabels.title}
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            {organizationLabels.newOrganization}
          </button>
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
            actionLabel={organizationLabels.newOrganization}
            onAction={openCreate}
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

      {deleting && (
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
