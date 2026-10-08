import React from "react";
import { ApiError } from "../api/client";
import { getCustomer } from "../api/customers";
import {
  assignFairStandProjectCustomer,
  deleteFairStandProject,
  listFairStandProjects,
  type FairStandProjectSummary,
} from "../api/fairStandProjects";
import { CustomerEntitySelect } from "../components/CustomerEntitySelect";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
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
import { CUSTOMER_READ } from "../permissions/customerPermissions";
import {
  PERMISSION_COST_ITEMS_READ,
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

function matchesSearch(row: FairStandProjectSummary, search: string, customerName: string): boolean {
  const q = search.trim().toLocaleLowerCase("tr-TR");
  if (!q) return true;
  const name = (row.name || "").toLocaleLowerCase("tr-TR");
  const customer = customerName.toLocaleLowerCase("tr-TR");
  return name.includes(q) || customer.includes(q);
}

type StandProjectsPageProps = {
  onOpenProject: (projectId: string) => void;
  onCreateProject: (customerId: string) => void;
  onCalculateProject: (projectId: string) => void;
};

export function StandProjectsPage({ onOpenProject, onCreateProject, onCalculateProject }: StandProjectsPageProps) {
  const granted = React.useMemo(() => getGrantedCorePermissions(), []);
  const canRead = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_READ);
  const canCalculate = canRead && hasGrantedCorePermission(granted, PERMISSION_COST_ITEMS_READ);
  const canCreate = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_CREATE);
  const canUpdate = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_UPDATE);
  const canDelete = hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_DELETE);
  const canReadCustomers = hasGrantedCorePermission(granted, CUSTOMER_READ);
  const canCreateForCustomer = canCreate && canReadCustomers;

  const [projects, setProjects] = React.useState<FairStandProjectSummary[]>([]);
  const [customerNames, setCustomerNames] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [deleting, setDeleting] = React.useState<FairStandProjectSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);
  const [pickingCustomer, setPickingCustomer] = React.useState(false);
  const [pickedCustomerId, setPickedCustomerId] = React.useState("");
  const [assigning, setAssigning] = React.useState<FairStandProjectSummary | null>(null);
  const [assignCustomerId, setAssignCustomerId] = React.useState("");
  const [assignBusy, setAssignBusy] = React.useState(false);

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

  React.useEffect(() => {
    if (!canReadCustomers) {
      setCustomerNames({});
      return;
    }
    const ids = [...new Set(projects.map((row) => row.customerId).filter(Boolean))];
    let cancelled = false;
    void Promise.all(
      ids.map(async (id) => {
        try {
          const customer = await getCustomer(id);
          return [id, customer.display_name] as const;
        } catch {
          return [id, ""] as const;
        }
      }),
    ).then((entries) => {
      if (cancelled) return;
      const next: Record<string, string> = {};
      for (const [id, name] of entries) {
        if (name) next[id] = name;
      }
      setCustomerNames(next);
    });
    return () => {
      cancelled = true;
    };
  }, [canReadCustomers, projects]);

  const filtered = React.useMemo(
    () => projects.filter((row) => matchesSearch(row, search, customerNames[row.customerId] || "")),
    [customerNames, projects, search],
  );

  const openCustomerPicker = () => {
    setPickedCustomerId("");
    setPickingCustomer(true);
  };

  const openAssign = (project: FairStandProjectSummary) => {
    setAssignCustomerId("");
    setAssigning(project);
  };

  const saveAssign = async () => {
    if (!canUpdate || !assigning || !assignCustomerId || assignCustomerId === assigning.customerId) return;
    setAssignBusy(true);
    setError(null);
    try {
      const updated = await assignFairStandProjectCustomer(assigning.id, assignCustomerId);
      setProjects((current) =>
        current.map((row) => (row.id === assigning.id ? { ...row, customerId: updated.customerId } : row)),
      );
      setAssigning(null);
      setAssignCustomerId("");
    } catch (assignError) {
      setError(
        assignError instanceof ApiError || assignError instanceof Error
          ? assignError.message
          : standProjectsLabels.assignError,
      );
    } finally {
      setAssignBusy(false);
    }
  };

  const headerActions = React.useMemo((): PageHeaderAction[] => {
    if (!canCreateForCustomer) return [];
    return [
      {
        id: "create-stand-project",
        label: standProjectsLabels.actionCreate,
        variant: "primary",
        onClick: openCustomerPicker,
      },
    ];
  }, [canCreateForCustomer]);

  const columns = React.useMemo((): UniversalDataTableColumn<FairStandProjectSummary>[] => {
    const cols: UniversalDataTableColumn<FairStandProjectSummary>[] = [
      {
        key: "name",
        title: standProjectsLabels.colName,
        sortable: false,
        render: (row) => row.name || "Adsız Proje",
      },
      {
        key: "customer",
        title: standProjectsLabels.colCustomer,
        sortable: false,
        render: (row) => customerNames[row.customerId] || standProjectsLabels.temporaryCustomer,
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
    if (canUpdate || canDelete || canCalculate) {
      cols.push({
        key: "actions",
        title: standProjectsLabels.colActions,
        sortable: false,
        render: (row) => (
          <TableRowActions>
            {canCalculate ? (
              <Button size="sm" variant="secondary" onClick={() => onCalculateProject(row.id)}>
                {standProjectsLabels.actionCalculate}
              </Button>
            ) : null}
            {canUpdate ? (
              <Button size="sm" variant="secondary" onClick={() => onOpenProject(row.id)}>
                {standProjectsLabels.actionEdit}
              </Button>
            ) : null}
            {canUpdate && canReadCustomers ? (
              <Button size="sm" variant="secondary" onClick={() => openAssign(row)}>
                {standProjectsLabels.actionAssignCustomer}
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
  }, [canCalculate, canDelete, canReadCustomers, canUpdate, customerNames, onCalculateProject, onOpenProject]);

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
          actionLabel={canCreateForCustomer ? standProjectsLabels.actionCreate : undefined}
          onAction={canCreateForCustomer ? openCustomerPicker : undefined}
        />
      ) : null}
      {!loading && filtered.length > 0 ? (
        <UniversalDataTable columns={columns} items={filtered} rowKey={(row) => row.id} />
      ) : null}
      {pickingCustomer && canCreateForCustomer ? (
        <Modal
          title={standProjectsLabels.pickCustomerTitle}
          onClose={() => setPickingCustomer(false)}
          footer={
            <Button
              variant="primary"
              disabled={!pickedCustomerId}
              onClick={() => {
                const customerId = pickedCustomerId;
                setPickingCustomer(false);
                onCreateProject(customerId);
              }}
            >
              {standProjectsLabels.pickCustomerConfirm}
            </Button>
          }
        >
          <p>{standProjectsLabels.pickCustomerDescription}</p>
          <CustomerEntitySelect
            id="stand-project-new-customer"
            value={pickedCustomerId}
            allowClear={false}
            onChange={setPickedCustomerId}
          />
        </Modal>
      ) : null}
      {assigning && canUpdate && canReadCustomers ? (
        <Modal
          title={standProjectsLabels.assignCustomerTitle}
          onClose={() => {
            if (!assignBusy) setAssigning(null);
          }}
          footer={
            <>
              <Button
                variant="secondary"
                disabled={assignBusy}
                onClick={() => setAssigning(null)}
              >
                İptal
              </Button>
              <Button
                variant="primary"
                disabled={
                  assignBusy || !assignCustomerId || assignCustomerId === assigning.customerId
                }
                onClick={() => {
                  void saveAssign();
                }}
              >
                {standProjectsLabels.assignCustomerConfirm}
              </Button>
            </>
          }
        >
          <p>{standProjectsLabels.assignCustomerDescription(assigning.name || "Adsız Proje")}</p>
          <CustomerEntitySelect
            id="stand-project-assign-customer"
            value={assignCustomerId}
            allowClear={false}
            onChange={setAssignCustomerId}
          />
        </Modal>
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
