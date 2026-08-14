import React from "react";

import {
  ApiError,
} from "../api/client";
import {
  createOrganization,
  deleteOrganization,
  listOrganizations,
  updateOrganization,
  type Organization,
} from "../api/organizations";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormField, FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../components/ui/UniversalDataTable";
import { organizationLabels } from "../labels/organizationLabels";

type FormMode = "create" | "edit" | null;

export function OrganizationsPage() {
  const [items, setItems] = React.useState<Organization[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [formMode, setFormMode] = React.useState<FormMode>(null);
  const [editing, setEditing] = React.useState<Organization | null>(null);
  const [name, setName] = React.useState("");
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

  const openCreate = () => {
    setEditing(null);
    setName("");
    setFormError(null);
    setFormMode("create");
  };

  const openEdit = (organization: Organization) => {
    setEditing(organization);
    setName(organization.name);
    setFormError(null);
    setFormMode("edit");
  };

  const closeForm = () => {
    if (saving) return;
    setFormMode(null);
    setEditing(null);
    setFormError(null);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setFormError(organizationLabels.nameRequired);
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (formMode === "edit" && editing) {
        await updateOrganization(editing.id, trimmedName);
      } else {
        await createOrganization(trimmedName);
      }
      setFormMode(null);
      setEditing(null);
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
    [],
  );

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

      {formMode && (
        <FormModal
          title={
            formMode === "edit"
              ? organizationLabels.editOrganization
              : organizationLabels.newOrganization
          }
          onClose={closeForm}
          formWidth="narrow"
          footer={
            <div className="form-actions">
              <button type="button" className="btn secondary" onClick={closeForm} disabled={saving}>
                {organizationLabels.cancel}
              </button>
              <button type="submit" form="organization-form" className="btn primary" disabled={saving}>
                {organizationLabels.save}
              </button>
            </div>
          }
        >
          <form id="organization-form" onSubmit={submit}>
            <FormField
              label={organizationLabels.organizationName}
              htmlFor="organization-name"
              required
              error={formError ?? undefined}
              fullWidth
            >
              <input
                id="organization-name"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoFocus
                disabled={saving}
              />
            </FormField>
          </form>
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
