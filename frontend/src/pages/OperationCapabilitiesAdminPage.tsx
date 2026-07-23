import React from "react";
import {
  listOperationTypes,
  updateOperationTypeCapabilities,
} from "../api/operations";
import { ApiError } from "../api/client";
import { OperationCapabilitiesEditForm } from "../components/admin/OperationCapabilitiesEditForm";
import { Banner } from "../components/ui/Banner";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import type {
  OperationTypeCapabilityKey,
  OperationTypeCatalogItem,
  UpdateOperationTypeCapabilitiesPayload,
} from "../types/operation";

const CAPABILITY_BADGES: Array<{
  key: OperationTypeCapabilityKey;
  label: string;
}> = [
  { key: "supports_pause", label: adminLabels.operationCapabilitySupportsPauseShort },
  { key: "supports_resume", label: adminLabels.operationCapabilitySupportsResumeShort },
  { key: "supports_retry", label: adminLabels.operationCapabilitySupportsRetryShort },
  { key: "supports_schedule", label: adminLabels.operationCapabilitySupportsScheduleShort },
  { key: "supports_items", label: adminLabels.operationCapabilitySupportsItemsShort },
];

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

export function OperationCapabilitiesAdminPage() {
  const [types, setTypes] = React.useState<OperationTypeCatalogItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<OperationTypeCatalogItem | null>(null);
  const [formSaving, setFormSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const loadTypes = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listOperationTypes();
      setTypes(response.items);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : adminLabels.operationCapabilitiesLoadError,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadTypes();
  }, [loadTypes]);

  React.useEffect(() => {
    if (!success) return undefined;
    const timer = window.setTimeout(() => setSuccess(null), 5000);
    return () => window.clearTimeout(timer);
  }, [success]);

  const openEdit = (item: OperationTypeCatalogItem) => {
    setEditing(item);
    setFormError(null);
  };

  const closeModal = React.useCallback(() => {
    setEditing(null);
    setFormError(null);
  }, []);

  const handleSave = async (payload: UpdateOperationTypeCapabilitiesPayload) => {
    if (!editing) return;
    setFormSaving(true);
    setFormError(null);
    try {
      await updateOperationTypeCapabilities(editing.key, payload);
      closeModal();
      setSuccess(adminLabels.operationCapabilitiesSaveSuccess);
      await loadTypes();
    } catch (err) {
      setFormError(
        err instanceof ApiError
          ? err.message
          : adminLabels.operationCapabilitiesSaveError,
      );
    } finally {
      setFormSaving(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<OperationTypeCatalogItem>[]>(
    () => [
      {
        key: "name",
        title: adminLabels.operationCapabilitiesColName,
        sortable: true,
        render: (item) => (
          <TableEntityLink onClick={() => openEdit(item)}>{item.name}</TableEntityLink>
        ),
      },
      {
        key: "is_active",
        title: adminLabels.operationCapabilitiesColActive,
        sortable: true,
        render: (item) =>
          item.is_active ? (
            <Badge variant="success">{adminLabels.operationCapabilitiesActiveBadge}</Badge>
          ) : (
            <Badge variant="neutral">{adminLabels.operationCapabilitiesInactiveBadge}</Badge>
          ),
      },
      {
        key: "capabilities",
        title: adminLabels.operationCapabilitiesColCapabilities,
        sortable: false,
        render: (item) => (
          <div className="operation-capabilities-badges" role="list">
            {CAPABILITY_BADGES.map((field) => (
              <span key={field.key} role="listitem">
                <Badge variant={item[field.key] ? "primary" : "neutral"}>{field.label}</Badge>
              </span>
            ))}
          </div>
        ),
      },
      {
        key: "updated_at",
        title: adminLabels.operationCapabilitiesColUpdatedAt,
        sortable: true,
        render: (item) => formatDateTime(item.updated_at),
      },
      {
        key: "actions",
        title: adminLabels.operationCapabilitiesColActions,
        sortable: false,
        render: (item) => (
          <TableRowActions>
            <button
              type="button"
              className="btn btn-sm secondary"
              onClick={() => openEdit(item)}
            >
              {adminLabels.operationCapabilitiesActionEdit}
            </button>
          </TableRowActions>
        ),
      },
    ],
    [],
  );

  return (
    <PageShell className="operation-capabilities-admin-page">
      <PageHeader
        title={adminLabels.operationCapabilitiesTitle}
        subtitle={adminLabels.operationCapabilitiesSubtitle}
      />

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <UniversalDataTable
        items={types}
        columns={columns}
        rowKey={(item) => item.key}
        loading={loading}
        error={error}
        onRetry={() => void loadTypes()}
        emptyState={
          error ? undefined : (
            <EmptyState
              title={adminLabels.operationCapabilitiesEmptyTitle}
              description={adminLabels.operationCapabilitiesEmptyDescription}
            />
          )
        }
      />

      {editing ? (
        <FormModal
          title={adminLabels.operationCapabilitiesEditTitle}
          onClose={closeModal}
          size="md"
        >
          <OperationCapabilitiesEditForm
            item={editing}
            saving={formSaving}
            error={formError}
            onCancel={closeModal}
            onSubmit={handleSave}
          />
        </FormModal>
      ) : null}
    </PageShell>
  );
}
