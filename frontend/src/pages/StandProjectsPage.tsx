import React from "react";
import { ApiError } from "../api/client";
import {
  deleteFairStandProject,
  listFairStandProjects,
  type FairStandProjectSummary,
} from "../api/fairStandProjects";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterPanel } from "../components/ui/FilterPanel";
import { LoadingState } from "../components/ui/LoadingState";
import { TableRowActions } from "../components/ui/TableRowActions";
import { FormField, TextInput } from "../components/ui/form";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { standProjectsLabels } from "../labels/standProjectsLabels";
import {
  getGrantedCorePermissions,
  hasGrantedCorePermission,
} from "../permissions/corePermissions";
import {
  PERMISSION_STAND_PROJECTS_CREATE,
  PERMISSION_STAND_PROJECTS_DELETE,
  PERMISSION_STAND_PROJECTS_READ,
  PERMISSION_STAND_PROJECTS_UPDATE,
} from "../permissions/navigationPermissions";

function formatProjectTimestamp(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return "—";
  try {
    return new Date(ms).toLocaleString("tr-TR");
  } catch {
    return "—";
  }
}

function matchesSearch(row: FairStandProjectSummary, search: string): boolean {
  const q = search.trim().toLocaleLowerCase("tr-TR");
  if (!q) return true;
  return (row.name || "").toLocaleLowerCase("tr-TR").includes(q);
}

type StandProjectsPageProps = {
  onOpenProject: (projectId: string) => void;
  onCreateProject: () => void;
};

export function StandProjectsPage({ onOpenProject, onCreateProject }: StandProjectsPageProps) {
  const granted = React.useMemo(() => getGrantedCorePermissions(), []);
  const canRead = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_READ);
  const canCreate = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_CREATE);
  const canUpdate = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_UPDATE);
  const canDelete = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_DELETE);

  const [projects, setProjects] = React.useState<FairStandProjectSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [deleting, setDeleting] = React.useState<FairStandProjectSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listFairStandProjects();
      setProjects(
        [...rows].sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0)),
      );
    } catch (loadError) {
      setError(
        loadError instanceof ApiError || loadError instanceof Error
          ? loadError.message
          : standProjectsLabels.loadError,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const filtered = React.useMemo(
    () => projects.filter((row) => matchesSearch(row, search)),
    [projects, search],
  );

  const headerActions = React.useMemo((): PageHeaderAction[] => {
    if (!canCreate) return [];
    return [
      {
        id: "create-stand-project",
        label: standProjectsLabels.actionCreate,
        variant: "primary",
        onClick: onCreateProject,
      },
    ];
  }, [canCreate, onCreateProject]);

  const columns = React.useMemo((): UniversalDataTableColumn<FairStandProjectSummary>[] => {
    const cols: UniversalDataTableColumn<FairStandProjectSummary>[] = [
      {
        key: "name",
        title: standProjectsLabels.colName,
        sortable: false,
        render: (row) => row.name || "Adsız Proje",
      },
      {
        key: "updated",
        title: standProjectsLabels.colUpdated,
        sortable: false,
        render: (row) => formatProjectTimestamp(row.updatedAt),
      },
      {
        key: "created",
        title: standProjectsLabels.colCreated,
        sortable: false,
        render: (row) => formatProjectTimestamp(row.createdAt),
      },
    ];
    if (canUpdate || canDelete) {
      cols.push({
        key: "actions",
        title: standProjectsLabels.colActions,
        sortable: false,
        render: (row) => (
          <TableRowActions>
            {canUpdate ? (
              <Button size="sm" variant="secondary" onClick={() => onOpenProject(row.id)}>
                {standProjectsLabels.actionEdit}
              </Button>
            ) : null}
            {canDelete ? (
              <Button size="sm" variant="danger" onClick={() => setDeleting(row)}>
                {standProjectsLabels.actionDelete}
              </Button>
            ) : null}
          </TableRowActions>
        ),
      });
    }
    return cols;
  }, [canDelete, canUpdate, onOpenProject]);

  const confirmDelete = async () => {
    if (!canDelete || !deleting) return;
    setDeleteBusy(true);
    setError(null);
    try {
      await deleteFairStandProject(deleting.id);
      setDeleting(null);
      await load();
    } catch (deleteError) {
      setError(
        deleteError instanceof ApiError || deleteError instanceof Error
          ? deleteError.message
          : standProjectsLabels.deleteError,
      );
    } finally {
      setDeleteBusy(false);
    }
  };

  if (!canRead) {
    return (
      <PageShell>
        <PageHeader title={standProjectsLabels.pageTitle} />
        <EmptyState
          title={standProjectsLabels.pageTitle}
          description="Bu sayfayı görüntüleme yetkiniz yok."
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title={standProjectsLabels.pageTitle}
        subtitle={standProjectsLabels.pageSubtitle}
        actions={headerActions}
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      <FilterPanel>
        <FormField label={standProjectsLabels.filterSearch} htmlFor="stand-projects-search">
          <TextInput
            id="stand-projects-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={standProjectsLabels.filterSearchPlaceholder}
          />
        </FormField>
      </FilterPanel>
      {loading ? <LoadingState /> : null}
      {!loading && filtered.length === 0 ? (
        <EmptyState
          title={standProjectsLabels.emptyTitle}
          description={standProjectsLabels.emptyDescription}
          actionLabel={canCreate ? standProjectsLabels.actionCreate : undefined}
          onAction={canCreate ? onCreateProject : undefined}
        />
      ) : null}
      {!loading && filtered.length > 0 ? (
        <UniversalDataTable columns={columns} items={filtered} rowKey={(row) => row.id} />
      ) : null}
      {deleting && canDelete ? (
        <ConfirmDialog
          title={standProjectsLabels.deleteConfirmTitle}
          message={standProjectsLabels.deleteConfirmDescription(deleting.name || "Adsız Proje")}
          confirmLabel={standProjectsLabels.deleteConfirmAction}
          variant="danger"
          loading={deleteBusy}
          onCancel={() => {
            if (!deleteBusy) setDeleting(null);
          }}
          onConfirm={() => {
            void confirmDelete();
          }}
        />
      ) : null}
    </PageShell>
  );
}
