import React from "react";

import { ApiError } from "../api/client";
import {
  createOrganizationRole,
  deleteOrganizationRole,
  deriveRoleTemplate,
  listManagedRoles,
  listPlatformPermissions,
  listRolePermissions,
  listRoleTemplates,
  previewPermissionLifecycle,
  previewTemplateSync,
  syncRoleTemplate,
  updateOrganizationRole,
  updateOrganizationRolePermissions,
  updatePermissionLifecycle,
  updateRoleTemplate,
  type ManagedRole,
  type RolePermission,
} from "../api/roleManagement";
import { getUserManagementContext, type ManagedOrganization } from "../api/userManagement";
import { Badge } from "../components/ui/Badge";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import {
  CheckboxField,
  FormDirtyHost,
  FormModal,
  SelectInput,
  TextInput,
  useFormDirtyCancel,
  useReportFormDirty,
} from "../components/ui/form";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TabPanel, Tabs, type TabItem } from "../components/ui/Tabs";
import { getGrantedCorePermissions } from "../permissions/corePermissions";

type Tab = "organization" | "templates" | "permissions";
type LifecycleFilter = "all" | RolePermission["lifecycle_state"];

interface RoleForm {
  name: string;
  slug: string;
  permissionIds: string[];
}

interface SyncConfirmTarget {
  role: ManagedRole;
  addCount: number;
  removeCount: number;
}

interface PermissionStateConfirmTarget {
  permission: RolePermission;
  state: RolePermission["lifecycle_state"];
  affectedRoles: number;
  affectedUsers: number;
}

const EMPTY_ROLE: RoleForm = { name: "", slug: "", permissionIds: [] };

const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : "İşlem tamamlanamadı.";

export function permissionGroup(code: string): string {
  return code.split(".").slice(0, 2).join(".");
}

export function samePermissionIds(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false;
  const rightSet = new Set(right);
  return left.every((id) => rightSet.has(id));
}

function groupTitle(group: string): string {
  const known: Record<string, string> = {
    "audit.logs": "Denetim Kayıtları",
    "settings.platform": "Sistem Ayarları",
    "jobs.platform": "Arka Plan İşleri",
    "notifications.platform": "Bildirimler",
    "identity.organizations": "Organizasyon Yönetimi",
    "identity.users": "Kullanıcı Yönetimi",
    "identity.roles": "Rol Yönetimi",
    "identity.role_templates": "Rol Şablonları",
    "identity.permissions": "İzin Yönetimi",
    "fair_crm.customers": "Müşteriler",
    "fair_crm.contacts": "İletişim Kişileri",
    "fair_crm.fairs": "Fuarlar",
    "fair_crm.participations": "Fuar Katılımları",
    "fair_crm.activities": "Aktiviteler",
    "fair_crm.todos": "Görevler",
    "fair_crm.imports": "Veri Aktarımı",
    "fair_crm.scraper": "Scraper",
    "fair_crm.operations": "Operasyonlar",
    "fair_crm.email_accounts": "E-posta Hesapları",
    "fair_crm.mail_templates": "E-posta Şablonları",
    "fair_crm.mail_send_operations": "E-posta Gönderim İşlemleri",
    "fair_crm.fair_emails": "Fuar E-postaları",
    "fair_crm.quote_templates": "Teklif Şablonları",
    "fair_crm.template_contents": "Şablon İçerikleri",
    "fair_crm.quotes": "Teklifler",
    "fair_crm.dashboard": "Gösterge Paneli",
    "fair_crm.cost_catalog": "Maliyet Kataloğu",
    "fair_crm.admin": "Sistem Yönetimi",
  };
  return known[group] ?? group;
}

function slugify(value: string): string {
  return value
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function PermissionMatrix({
  permissions,
  selected,
  disabled = false,
  onChange,
}: {
  permissions: RolePermission[];
  selected: string[];
  disabled?: boolean;
  onChange: (ids: string[]) => void;
}) {
  const instanceId = React.useId().replace(/:/g, "");
  const [query, setQuery] = React.useState("");
  const [activeGroup, setActiveGroup] = React.useState("");
  const selectedSet = React.useMemo(() => new Set(selected), [selected]);

  const groupedPermissions = React.useMemo(() => {
    const result = new Map<string, RolePermission[]>();
    permissions.forEach((permission) => {
      const group = permissionGroup(permission.code);
      result.set(group, [...(result.get(group) ?? []), permission]);
    });
    return result;
  }, [permissions]);

  const groupKeys = React.useMemo(
    () => [...groupedPermissions.keys()].sort((left, right) =>
      groupTitle(left).localeCompare(groupTitle(right), "tr"),
    ),
    [groupedPermissions],
  );

  React.useEffect(() => {
    if (!groupKeys.length) {
      setActiveGroup("");
      return;
    }
    if (!activeGroup || !groupedPermissions.has(activeGroup)) {
      setActiveGroup(groupKeys[0]);
    }
  }, [activeGroup, groupKeys, groupedPermissions]);

  const groupItems = activeGroup ? groupedPermissions.get(activeGroup) ?? [] : [];
  const normalizedQuery = query.trim().toLocaleLowerCase("tr-TR");
  const visibleItems = groupItems.filter((permission) => {
    if (!normalizedQuery) return true;
    return `${permission.code} ${permission.description}`
      .toLocaleLowerCase("tr-TR")
      .includes(normalizedQuery);
  });

  const activeItems = groupItems.filter((item) => item.lifecycle_state === "active");
  const selectedCount = activeItems.filter((item) => selectedSet.has(item.id)).length;
  const allSelected = activeItems.length > 0 && selectedCount === activeItems.length;

  const toggleGroup = (checked: boolean) => {
    const next = new Set(selected);
    activeItems.forEach((permission) => {
      if (checked) next.add(permission.id);
      else next.delete(permission.id);
    });
    onChange([...next]);
  };

  return (
    <div className="permission-matrix">
      <div className="permission-matrix-toolbar">
        <SelectInput
          id={`permission-group-${instanceId}`}
          value={activeGroup}
          onChange={(event) => {
            setActiveGroup(event.target.value);
            setQuery("");
          }}
          aria-label="İzin kategorisi"
          disabled={disabled || groupKeys.length === 0}
        >
          {groupKeys.map((group) => {
            const items = groupedPermissions.get(group) ?? [];
            const count = items.filter((item) => selectedSet.has(item.id)).length;
            return (
              <option key={group} value={group}>
                {groupTitle(group)} ({count}/{items.length})
              </option>
            );
          })}
        </SelectInput>
        <label className="permission-search" htmlFor={`permission-search-${instanceId}`}>
          <span className="sr-only">İzin ara</span>
          <TextInput
            id={`permission-search-${instanceId}`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Seçili kategoride izin ara…"
            disabled={disabled || !activeGroup}
          />
        </label>
        <Badge variant="primary">{selected.length} izin seçili</Badge>
      </div>

      {activeGroup ? (
        <section className="permission-group" aria-label={groupTitle(activeGroup)}>
          <header className="permission-group-header">
            <div>
              <strong>{groupTitle(activeGroup)}</strong>
              <code>{activeGroup}</code>
            </div>
            <div className="permission-group-toggle">
              <CheckboxField
                id={`permission-group-toggle-${instanceId}`}
                label={`${groupTitle(activeGroup)} kategorisindeki tüm izinleri seç`}
                checked={allSelected}
                indeterminate={selectedCount > 0 && !allSelected}
                disabled={disabled || activeItems.length === 0}
                hideLabel
                onChange={toggleGroup}
              />
              <span>{selectedCount}/{activeItems.length}</span>
            </div>
          </header>
          <div className="permission-items">
            {visibleItems.map((permission) => (
              <div className="permission-item" key={permission.id}>
                <CheckboxField
                  id={`permission-${instanceId}-${permission.id}`}
                  label={`${permission.code}: ${permission.description}`}
                  checked={selectedSet.has(permission.id)}
                  disabled={disabled || permission.lifecycle_state !== "active"}
                  hideLabel
                  onChange={(checked) => onChange(
                    checked
                      ? [...selected, permission.id]
                      : selected.filter((id) => id !== permission.id),
                  )}
                />
                <span className="permission-item-copy">
                  <code>{permission.code}</code>
                  <small>{permission.description}</small>
                </span>
                {permission.lifecycle_state !== "active" ? (
                  <Badge variant="warning">{permission.lifecycle_state}</Badge>
                ) : null}
              </div>
            ))}
            {!visibleItems.length ? (
              <EmptyState
                title="Eşleşen izin bulunamadı"
                description="Arama ifadesini değiştirin."
              />
            ) : null}
          </div>
        </section>
      ) : (
        <EmptyState title="İzin bulunamadı" description="Bu kapsamda atanabilir izin yok." />
      )}
    </div>
  );
}

function RolePermissionPreview({ role, permissions }: { role: ManagedRole; permissions: RolePermission[] }) {
  const rolePermissions = permissions.filter((permission) => role.permission_ids.includes(permission.id));
  const grouped = new Map<string, number>();
  rolePermissions.forEach((permission) => {
    const group = permissionGroup(permission.code);
    grouped.set(group, (grouped.get(group) ?? 0) + 1);
  });
  return (
    <div className="role-permission-preview">
      {[...grouped.entries()].map(([group, count]) => (
        <span className="role-permission-chip" key={group}>
          {groupTitle(group)} <strong>{count}</strong>
        </span>
      ))}
      {!rolePermissions.length ? <span className="muted">Bu role atanmış aktif izin yok.</span> : null}
    </div>
  );
}

function RoleEditorModal({
  editing,
  form,
  permissions,
  saving,
  onChange,
  onClose,
  onSubmit,
}: {
  editing: ManagedRole | null;
  form: RoleForm;
  permissions: RolePermission[];
  saving: boolean;
  onChange: React.Dispatch<React.SetStateAction<RoleForm>>;
  onClose: () => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  const baseline = React.useRef(form);
  useReportFormDirty(form, baseline.current);
  const requestClose = useFormDirtyCancel(onClose);

  return (
    <FormModal
      title={editing ? "Rolü Düzenle" : "Yeni Rol"}
      onClose={requestClose}
      formWidth="wide"
      footer={(
        <>
          <Button variant="secondary" onClick={requestClose} disabled={saving}>Vazgeç</Button>
          <Button
            variant="primary"
            type="submit"
            form="role-management-form"
            loading={saving}
            disabled={!form.name.trim() || !form.slug}
          >
            Kaydet
          </Button>
        </>
      )}
    >
      <form id="role-management-form" className="crm-form-stack" onSubmit={onSubmit}>
        <div className="role-form-grid">
          <label className="form-field" htmlFor="role-name">
            <span className="form-label">Rol adı *</span>
            <TextInput
              id="role-name"
              value={form.name}
              onChange={(event) => onChange((current) => ({
                ...current,
                name: event.target.value,
                ...(!editing ? { slug: slugify(event.target.value) } : {}),
              }))}
              required
            />
          </label>
          <label className="form-field" htmlFor="role-slug">
            <span className="form-label">Rol kodu *</span>
            <TextInput
              id="role-slug"
              value={form.slug}
              onChange={(event) => onChange((current) => ({
                ...current,
                slug: slugify(event.target.value),
              }))}
              required
            />
          </label>
        </div>
        <PermissionMatrix
          permissions={permissions}
          selected={form.permissionIds}
          disabled={saving}
          onChange={(ids) => onChange((current) => ({ ...current, permissionIds: ids }))}
        />
      </form>
    </FormModal>
  );
}

function DerivedRoleModal({
  templateName,
  organizationName,
  form,
  saving,
  onChange,
  onClose,
  onSubmit,
}: {
  templateName: string;
  organizationName: string;
  form: RoleForm;
  saving: boolean;
  onChange: React.Dispatch<React.SetStateAction<RoleForm>>;
  onClose: () => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  const baseline = React.useRef(form);
  useReportFormDirty(form, baseline.current);
  const requestClose = useFormDirtyCancel(onClose);

  return (
    <FormModal
      title={`${templateName} şablonundan rol oluştur`}
      onClose={requestClose}
      footer={(
        <>
          <Button variant="secondary" onClick={requestClose} disabled={saving}>Vazgeç</Button>
          <Button
            variant="primary"
            type="submit"
            form="derive-role-form"
            loading={saving}
            disabled={!form.name.trim() || !form.slug}
          >
            Rolü Oluştur
          </Button>
        </>
      )}
    >
      <form id="derive-role-form" className="crm-form-stack" onSubmit={onSubmit}>
        <Banner variant="info">
          Rol, {organizationName} organizasyonuna atanacak ve şablonun mevcut izinlerini alacak.
        </Banner>
        <label className="form-field" htmlFor="derived-role-name">
          <span className="form-label">Rol adı *</span>
          <TextInput
            id="derived-role-name"
            value={form.name}
            onChange={(event) => onChange((current) => ({ ...current, name: event.target.value }))}
            required
          />
        </label>
        <label className="form-field" htmlFor="derived-role-slug">
          <span className="form-label">Rol kodu *</span>
          <TextInput
            id="derived-role-slug"
            value={form.slug}
            onChange={(event) => onChange((current) => ({ ...current, slug: slugify(event.target.value) }))}
            required
          />
        </label>
      </form>
    </FormModal>
  );
}

export function RoleManagementPage() {
  const grantedPermissions = getGrantedCorePermissions();
  const [tab, setTab] = React.useState<Tab>("organization");
  const [isSuperAdmin, setIsSuperAdmin] = React.useState(false);
  const [organizations, setOrganizations] = React.useState<ManagedOrganization[]>([]);
  const [organizationId, setOrganizationId] = React.useState("");
  const [roles, setRoles] = React.useState<ManagedRole[]>([]);
  const [templates, setTemplates] = React.useState<ManagedRole[]>([]);
  const [permissions, setPermissions] = React.useState<RolePermission[]>([]);
  const [templateDrafts, setTemplateDrafts] = React.useState<Record<string, string[]>>({});
  const [expandedRoles, setExpandedRoles] = React.useState<Set<string>>(new Set());
  const [permissionQuery, setPermissionQuery] = React.useState("");
  const [lifecycleFilter, setLifecycleFilter] = React.useState<LifecycleFilter>("all");
  const [loading, setLoading] = React.useState(true);
  const [organizationLoading, setOrganizationLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<ManagedRole | null | undefined>(undefined);
  const [form, setForm] = React.useState<RoleForm>(EMPTY_ROLE);
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<ManagedRole | null>(null);
  const [deriveSource, setDeriveSource] = React.useState<ManagedRole | null>(null);
  const [syncConfirmTarget, setSyncConfirmTarget] = React.useState<SyncConfirmTarget | null>(null);
  const [permissionStateConfirmTarget, setPermissionStateConfirmTarget] = React.useState<PermissionStateConfirmTarget | null>(null);

  const selectedOrganization = organizations.find((item) => item.id === organizationId);
  const canCreateRole = isSuperAdmin || grantedPermissions.has("identity.roles.create");
  const canUpdateRole = isSuperAdmin || grantedPermissions.has("identity.roles.update");
  const canDeleteRole = isSuperAdmin || grantedPermissions.has("identity.roles.delete");
  const canReadPermissions = isSuperAdmin || grantedPermissions.has("identity.permissions.read");

  const loadContext = React.useCallback(async () => {
    const context = await getUserManagementContext();
    setIsSuperAdmin(context.is_super_admin);
    setOrganizations(context.organizations);
    setOrganizationId((current) => (
      context.organizations.some((item) => item.id === current)
        ? current
        : context.organizations[0]?.id ?? ""
    ));
    if (context.is_super_admin) {
      const [templateResult, permissionResult] = await Promise.all([
        listRoleTemplates(),
        listPlatformPermissions(),
      ]);
      setTemplates(templateResult);
      setPermissions(permissionResult);
      setTemplateDrafts(Object.fromEntries(
        templateResult.map((template) => [template.id, template.permission_ids]),
      ));
    }
  }, []);

  const loadOrganization = React.useCallback(async () => {
    if (!organizationId) {
      setRoles([]);
      return;
    }
    setOrganizationLoading(true);
    try {
      const [roleResult, permissionResult] = await Promise.all([
        listManagedRoles(organizationId),
        isSuperAdmin
          ? listPlatformPermissions()
          : canReadPermissions
            ? listRolePermissions(organizationId)
            : Promise.resolve([]),
      ]);
      setRoles(roleResult);
      setPermissions(permissionResult);
    } finally {
      setOrganizationLoading(false);
    }
  }, [canReadPermissions, organizationId, isSuperAdmin]);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    loadContext()
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [loadContext]);

  React.useEffect(() => {
    loadOrganization().catch((err) => setError(errorMessage(err)));
  }, [loadOrganization]);

  const openCreateRole = () => {
    setEditing(null);
    setForm(EMPTY_ROLE);
  };

  const saveRole = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!organizationId) return;
    setSaving(true);
    setError(null);
    try {
      if (editing) {
        await updateOrganizationRole(organizationId, editing.id, {
          name: form.name.trim(),
          slug: form.slug,
        });
        await updateOrganizationRolePermissions(organizationId, editing.id, form.permissionIds);
      } else {
        await createOrganizationRole(organizationId, {
          name: form.name.trim(),
          slug: form.slug,
          permission_ids: form.permissionIds,
        });
      }
      setSuccess(editing ? "Rol güncellendi." : "Rol oluşturuldu.");
      setEditing(undefined);
      await loadOrganization();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const saveTemplate = async (template: ManagedRole) => {
    const permissionIds = templateDrafts[template.id] ?? template.permission_ids;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateRoleTemplate(template.id, permissionIds);
      setTemplates((current) => current.map((item) => item.id === updated.id ? updated : item));
      setTemplateDrafts((current) => ({ ...current, [updated.id]: updated.permission_ids }));
      setSuccess(`${template.name} şablonu güncellendi. Mevcut organizasyon rolleri otomatik değiştirilmedi.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const derive = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!deriveSource || !organizationId) return;
    setSaving(true);
    setError(null);
    try {
      await deriveRoleTemplate(deriveSource.id, {
        organization_id: organizationId,
        name: form.name.trim(),
        slug: form.slug,
      });
      setDeriveSource(null);
      setSuccess(`${deriveSource.name} şablonundan organizasyon rolü oluşturuldu.`);
      await loadOrganization();
      setTab("organization");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const requestSync = async (role: ManagedRole) => {
    if (!role.source_template_role_id) return;
    setSaving(true);
    setError(null);
    try {
      const preview = (await previewTemplateSync(role.source_template_role_id, [role.id]))[0];
      if (!preview) return;
      setSyncConfirmTarget({ role, addCount: preview.add_count, removeCount: preview.remove_count });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const confirmSync = async () => {
    const target = syncConfirmTarget;
    if (!target?.role.source_template_role_id) return;
    setSaving(true);
    setError(null);
    try {
      await syncRoleTemplate(target.role.source_template_role_id, [target.role.id]);
      setSyncConfirmTarget(null);
      setSuccess("Rol, kaynak şablonun güncel sürümüyle eşitlendi.");
      await loadOrganization();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const requestPermissionStateChange = async (
    permission: RolePermission,
    state: RolePermission["lifecycle_state"],
  ) => {
    setSaving(true);
    setError(null);
    try {
      const preview = await previewPermissionLifecycle(permission.id, state);
      setPermissionStateConfirmTarget({
        permission,
        state,
        affectedRoles: preview.affected_roles,
        affectedUsers: preview.affected_users,
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const confirmPermissionStateChange = async () => {
    const target = permissionStateConfirmTarget;
    if (!target) return;
    setSaving(true);
    setError(null);
    try {
      await updatePermissionLifecycle(
        target.permission.id,
        target.state,
        target.state === "active" ? undefined : "Platform yöneticisi tarafından değiştirildi",
      );
      setPermissionStateConfirmTarget(null);
      await Promise.all([loadContext(), loadOrganization()]);
      setSuccess(`İzin durumu “${target.state}” olarak güncellendi.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const tabs: TabItem<Tab>[] = [
    { id: "organization", label: "Organizasyon Rolleri", badge: roles.length },
    ...(isSuperAdmin ? [
      { id: "templates" as const, label: "Varsayılan Şablonlar", badge: templates.length },
      { id: "permissions" as const, label: "Global İzin Yönetimi", badge: permissions.filter((item) => item.lifecycle_state !== "active").length },
    ] : []),
  ];

  const filteredPermissions = permissions.filter((permission) => {
    const matchesState = lifecycleFilter === "all" || permission.lifecycle_state === lifecycleFilter;
    const query = permissionQuery.trim().toLocaleLowerCase("tr-TR");
    const matchesQuery = !query || `${permission.code} ${permission.description}`
      .toLocaleLowerCase("tr-TR")
      .includes(query);
    return matchesState && matchesQuery;
  });

  if (loading) {
    return (
      <PageShell>
        <PageHeader title="Roller ve Yetkiler" subtitle="Rol kataloğu hazırlanıyor." />
        <LoadingState message="Roller ve izinler yükleniyor…" />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title="Roller ve Yetkiler"
        subtitle="Organizasyon rollerini, varsayılan şablonları ve platform izinlerini tek noktadan yönetin."
        actions={tab === "organization" ? (
          <Button variant="primary" onClick={openCreateRole} disabled={!organizationId || saving || !canCreateRole}>
            Yeni Rol
          </Button>
        ) : undefined}
      />

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <Card as="section" className="role-scope-card" aria-label="Rol kapsamı">
        <label className="form-field role-organization-field" htmlFor="role-organization">
          <span className="form-label">Organizasyon</span>
          <SelectInput id="role-organization" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
            <option value="">Organizasyon seçin</option>
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>{organization.name}</option>
            ))}
          </SelectInput>
        </label>
        <div className="role-summary-grid" aria-label="Rol özeti">
          <div><strong>{roles.length}</strong><span>Atanabilir rol</span></div>
          <div><strong>{roles.filter((role) => !role.is_protected).length}</strong><span>Düzenlenebilir rol</span></div>
          <div><strong>{permissions.filter((item) => item.lifecycle_state === "active").length}</strong><span>Aktif izin</span></div>
        </div>
      </Card>

      <Tabs items={tabs} active={tab} onChange={setTab} ariaLabel="Rol yönetimi bölümleri" />

      <TabPanel id="panel-organization" labelledBy="tab-organization" active={tab === "organization"}>
        <div className="section-header role-section-header">
          <div>
            <h2 className="section-title">{selectedOrganization?.name ?? "Organizasyon"} rolleri</h2>
            <p className="section-description muted">Kullanıcılar bu organizasyonda aşağıdaki rollerden birine atanabilir.</p>
          </div>
        </div>
        {organizationLoading ? <LoadingState message="Organizasyon rolleri yükleniyor…" /> : (
          <div className="role-card-grid">
            {roles.map((role) => {
              const isExpanded = expandedRoles.has(role.id);
              const sourceTemplate = templates.find((item) => item.id === role.source_template_role_id);
              const isOutdated = Boolean(sourceTemplate && role.source_template_version !== null && role.source_template_version < sourceTemplate.template_version);
              return (
                <Card as="section" className={`role-card ${role.is_protected ? "role-card-protected" : ""}`} key={role.id}>
                  <div className="role-card-topline">
                    <div className="role-card-title">
                      <span className={`role-kind-icon ${role.is_protected ? "protected" : "custom"}`} aria-hidden="true">{role.is_protected ? "◆" : "◇"}</span>
                      <div><h3>{role.name}</h3><code>{role.slug}</code></div>
                    </div>
                    <Badge variant={role.is_protected ? "primary" : role.source_template_role_id ? "info" : "neutral"}>
                      {role.is_protected ? "Sistem rolü" : role.source_template_role_id ? "Şablondan türetildi" : "Özel rol"}
                    </Badge>
                  </div>
                  <p className="role-card-description">
                    {role.is_protected
                      ? "OrganizationAdmin, organizasyondaki tüm aktif izinleri otomatik olarak alır ve doğrudan değiştirilemez."
                      : role.source_template_role_id
                        ? `Kaynak şablon sürümü: ${role.source_template_version ?? "—"}${isOutdated ? " · Güncelleme bekliyor" : " · Güncel"}`
                        : "Bu organizasyon için özel olarak oluşturulmuş bağımsız rol."}
                  </p>
                  <div className="role-card-metrics">
                    <div><strong>{role.permission_ids.length}</strong><span>izin</span></div>
                    <div><strong>{role.is_assignable ? "Aktif" : "Kapalı"}</strong><span>atanabilirlik</span></div>
                    {role.source_template_role_id ? <div><strong>{role.permissions_customized ? "Özel" : "Standart"}</strong><span>izin seti</span></div> : null}
                  </div>
                  {isExpanded ? <RolePermissionPreview role={role} permissions={permissions} /> : null}
                  <footer className="role-card-actions">
                    <Button variant="secondary" size="sm" onClick={() => setExpandedRoles((current) => {
                      const next = new Set(current);
                      if (next.has(role.id)) next.delete(role.id); else next.add(role.id);
                      return next;
                    })}>{isExpanded ? "İzinleri gizle" : "İzinleri göster"}</Button>
                    {!role.is_protected ? (
                      <>
                        {canUpdateRole ? <Button variant="secondary" size="sm" onClick={() => { setEditing(role); setForm({ name: role.name, slug: role.slug, permissionIds: role.permission_ids }); }}>Düzenle</Button> : null}
                        {role.source_template_role_id && isSuperAdmin ? <Button variant="secondary" size="sm" onClick={() => void requestSync(role)} loading={saving}>Şablondan güncelle</Button> : null}
                        {canDeleteRole ? <Button variant="danger" size="sm" onClick={() => setDeleteTarget(role)}>Sil</Button> : null}
                      </>
                    ) : null}
                  </footer>
                </Card>
              );
            })}
            {!roles.length ? <EmptyState title="Bu organizasyonda atanabilir rol yok" description="Özel rol oluşturun veya varsayılan bir şablondan rol türetin." actionLabel={canCreateRole ? "Yeni Rol" : undefined} onAction={canCreateRole ? openCreateRole : undefined} /> : null}
          </div>
        )}
      </TabPanel>

      <TabPanel id="panel-templates" labelledBy="tab-templates" active={tab === "templates"}>
        <div className="section-header role-section-header">
          <div><h2 className="section-title">Varsayılan rol şablonları</h2><p className="section-description muted">Şablon değişiklikleri yeni türetilecek rollere uygulanır. Mevcut roller ayrıca senkronize edilmelidir.</p></div>
        </div>
        <div className="template-list">
          {templates.map((template) => {
            const draft = templateDrafts[template.id] ?? template.permission_ids;
            const hasChanges = !samePermissionIds(draft, template.permission_ids);
            return (
              <Card as="section" className="template-card" key={template.id}>
                <header className="template-card-header">
                  <div><div className="template-title-row"><h3>{template.name}</h3><Badge variant="info">Şablon</Badge></div><p><code>{template.slug}</code> · Sürüm {template.template_version} · Doğrudan kullanıcıya atanamaz</p></div>
                  <div className="template-actions">
                    <Button variant="secondary" onClick={() => { setDeriveSource(template); setForm({ ...EMPTY_ROLE, name: template.name, slug: `${template.slug}_${selectedOrganization?.slug ?? organizationId.slice(0, 6)}` }); }} disabled={!organizationId || saving}>Organizasyona ata</Button>
                    <Button variant="primary" onClick={() => void saveTemplate(template)} loading={saving} disabled={!hasChanges}>{hasChanges ? "Şablonu Kaydet" : "Değişiklik Yok"}</Button>
                  </div>
                </header>
                {hasChanges ? <Banner variant="info">Kaydedilmemiş izin değişiklikleri var.</Banner> : null}
                <PermissionMatrix permissions={permissions.filter((item) => item.lifecycle_state === "active")} selected={draft} disabled={saving} onChange={(ids) => setTemplateDrafts((current) => ({ ...current, [template.id]: ids }))} />
              </Card>
            );
          })}
        </div>
      </TabPanel>

      <TabPanel id="panel-permissions" labelledBy="tab-permissions" active={tab === "permissions"}>
        <Card as="section" className="permission-lifecycle-notice"><strong>Global etki alanı</strong><p>Bir izni kilitlemek veya devre dışı bırakmak, OrganizationAdmin dahil tüm rollerden kaldırır. Super Admin erişimi etkilenmez.</p></Card>
        <div className="permission-lifecycle-toolbar">
          <TextInput id="global-permission-search" value={permissionQuery} onChange={(event) => setPermissionQuery(event.target.value)} placeholder="İzin ara…" aria-label="Global izin ara" />
          <SelectInput id="permission-lifecycle-filter" value={lifecycleFilter} onChange={(event) => setLifecycleFilter(event.target.value as LifecycleFilter)} aria-label="İzin durumu">
            <option value="all">Tüm durumlar</option><option value="active">Aktif</option><option value="locked">Kilitli</option><option value="inactive">Devre dışı</option>
          </SelectInput>
        </div>
        <div className="permission-lifecycle-list">
          {filteredPermissions.map((permission) => (
            <Card as="section" className="permission-lifecycle-row" key={permission.id}>
              <div className="permission-lifecycle-copy">
                <div><code>{permission.code}</code><Badge variant={permission.lifecycle_state === "active" ? "success" : permission.lifecycle_state === "locked" ? "warning" : "danger"}>{permission.lifecycle_state === "active" ? "Aktif" : permission.lifecycle_state === "locked" ? "Kilitli" : "Devre dışı"}</Badge>{!permission.is_assignable ? <Badge variant="neutral">Platform yönetimli</Badge> : null}</div>
                <p>{permission.description}</p>
              </div>
              <div className="permission-lifecycle-actions">
                {permission.lifecycle_state === "active" ? (
                  <><Button variant="secondary" size="sm" loading={saving} onClick={() => void requestPermissionStateChange(permission, "locked")}>Kilitle</Button><Button variant="danger" size="sm" loading={saving} onClick={() => void requestPermissionStateChange(permission, "inactive")}>Devre dışı bırak</Button></>
                ) : <Button variant="secondary" size="sm" loading={saving} onClick={() => void requestPermissionStateChange(permission, "active")}>Aktifleştir</Button>}
              </div>
            </Card>
          ))}
          {!filteredPermissions.length ? <EmptyState title="İzin bulunamadı" description="Arama veya durum filtresini değiştirin." /> : null}
        </div>
      </TabPanel>

      {editing !== undefined ? (
        <FormDirtyHost onClose={() => setEditing(undefined)} confirmClassName="modal-backdrop-nested">
          <RoleEditorModal editing={editing} form={form} permissions={permissions.filter((item) => item.lifecycle_state === "active" && item.is_assignable)} saving={saving} onChange={setForm} onClose={() => setEditing(undefined)} onSubmit={saveRole} />
        </FormDirtyHost>
      ) : null}

      {deriveSource ? (
        <FormDirtyHost onClose={() => setDeriveSource(null)} confirmClassName="modal-backdrop-nested">
          <DerivedRoleModal templateName={deriveSource.name} organizationName={selectedOrganization?.name ?? "seçili organizasyon"} form={form} saving={saving} onChange={setForm} onClose={() => setDeriveSource(null)} onSubmit={derive} />
        </FormDirtyHost>
      ) : null}

      {deleteTarget ? <ConfirmDialog title="Rolü Sil" message={`${deleteTarget.name} rolü silinecek. Aktif kullanıcıya atanmışsa işlem güvenlik nedeniyle engellenir.`} confirmLabel="Rolü Sil" variant="danger" loading={saving} onCancel={() => setDeleteTarget(null)} onConfirm={() => { if (!organizationId) return; setSaving(true); setError(null); void deleteOrganizationRole(organizationId, deleteTarget.id).then(async () => { setDeleteTarget(null); setSuccess("Rol silindi."); await loadOrganization(); }).catch((err) => setError(errorMessage(err))).finally(() => setSaving(false)); }} /> : null}
      {syncConfirmTarget ? <ConfirmDialog title="Rolü Şablonla Güncelle" message={`${syncConfirmTarget.role.name}: ${syncConfirmTarget.addCount} izin eklenecek, ${syncConfirmTarget.removeCount} izin kaldırılacak.`} confirmLabel="Güncelle" loading={saving} onCancel={() => setSyncConfirmTarget(null)} onConfirm={() => void confirmSync()} /> : null}
      {permissionStateConfirmTarget ? <ConfirmDialog title="İzin Durumunu Değiştir" message={`${permissionStateConfirmTarget.permission.code}: ${permissionStateConfirmTarget.affectedRoles} rol ve ${permissionStateConfirmTarget.affectedUsers} kullanıcı etkilenecek.`} confirmLabel="Uygula" variant={permissionStateConfirmTarget.state === "inactive" ? "danger" : "default"} loading={saving} onCancel={() => setPermissionStateConfirmTarget(null)} onConfirm={() => void confirmPermissionStateChange()} /> : null}
    </PageShell>
  );
}
