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
import { Banner } from "../components/ui/Banner";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
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
    "identity.users": "Kullanıcı Yönetimi",
    "identity.roles": "Rol Yönetimi",
    "identity.role_templates": "Rol Şablonları",
    "identity.permissions": "İzin Yönetimi",
    "fair_crm.customers": "Müşteriler",
    "fair_crm.contacts": "İletişim Kişileri",
    "fair_crm.fairs": "Fuarlar",
    "fair_crm.activities": "Aktiviteler",
    "fair_crm.todos": "Görevler",
    "fair_crm.imports": "Veri Aktarımı",
    "fair_crm.email_accounts": "E-posta Hesapları",
    "fair_crm.mail_templates": "E-posta Şablonları",
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
  const [query, setQuery] = React.useState("");
  const selectedSet = React.useMemo(() => new Set(selected), [selected]);
  const normalizedQuery = query.trim().toLocaleLowerCase("tr-TR");
  const visiblePermissions = React.useMemo(
    () => permissions.filter((permission) => {
      if (!normalizedQuery) return true;
      return `${permission.code} ${permission.description}`
        .toLocaleLowerCase("tr-TR")
        .includes(normalizedQuery);
    }),
    [normalizedQuery, permissions],
  );
  const groups = React.useMemo(() => {
    const result = new Map<string, RolePermission[]>();
    visiblePermissions.forEach((permission) => {
      const group = permissionGroup(permission.code);
      result.set(group, [...(result.get(group) ?? []), permission]);
    });
    return [...result.entries()];
  }, [visiblePermissions]);

  const toggleGroup = (items: RolePermission[], checked: boolean) => {
    const next = new Set(selected);
    items.forEach((permission) => {
      if (permission.lifecycle_state !== "active") return;
      if (checked) next.add(permission.id);
      else next.delete(permission.id);
    });
    onChange([...next]);
  };

  return (
    <div className="permission-matrix">
      <div className="permission-matrix-toolbar">
        <label className="permission-search">
          <span className="sr-only">İzin ara</span>
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="İzin kodu veya açıklama ara…"
          />
        </label>
        <span className="badge badge-primary">{selected.length} izin seçili</span>
      </div>
      <div className="permission-groups">
        {groups.map(([group, items]) => {
          const activeItems = items.filter((item) => item.lifecycle_state === "active");
          const selectedCount = activeItems.filter((item) => selectedSet.has(item.id)).length;
          const allSelected = activeItems.length > 0 && selectedCount === activeItems.length;
          return (
            <section className="permission-group" key={group}>
              <header className="permission-group-header">
                <div>
                  <strong>{groupTitle(group)}</strong>
                  <code>{group}</code>
                </div>
                <label className="permission-group-toggle">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    disabled={disabled || activeItems.length === 0}
                    onChange={(event) => toggleGroup(activeItems, event.target.checked)}
                  />
                  <span>{selectedCount}/{activeItems.length}</span>
                </label>
              </header>
              <div className="permission-items">
                {items.map((permission) => (
                  <label className="permission-item" key={permission.id}>
                    <input
                      type="checkbox"
                      checked={selectedSet.has(permission.id)}
                      disabled={disabled || permission.lifecycle_state !== "active"}
                      onChange={(event) => onChange(
                        event.target.checked
                          ? [...selected, permission.id]
                          : selected.filter((id) => id !== permission.id),
                      )}
                    />
                    <span className="permission-item-copy">
                      <code>{permission.code}</code>
                      <small>{permission.description}</small>
                    </span>
                    {permission.lifecycle_state !== "active" ? (
                      <span className="badge badge-warning">{permission.lifecycle_state}</span>
                    ) : null}
                  </label>
                ))}
              </div>
            </section>
          );
        })}
        {!groups.length ? (
          <EmptyState title="Eşleşen izin bulunamadı" description="Arama ifadesini değiştirin." />
        ) : null}
      </div>
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

  const sync = async (role: ManagedRole) => {
    if (!role.source_template_role_id) return;
    setSaving(true);
    setError(null);
    try {
      const preview = (await previewTemplateSync(role.source_template_role_id, [role.id]))[0];
      if (!preview) return;
      const confirmed = window.confirm(
        `${role.name}: ${preview.add_count} izin eklenecek, ${preview.remove_count} izin kaldırılacak. Devam edilsin mi?`,
      );
      if (!confirmed) return;
      await syncRoleTemplate(role.source_template_role_id, [role.id]);
      setSuccess("Rol, kaynak şablonun güncel sürümüyle eşitlendi.");
      await loadOrganization();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const changePermissionState = async (
    permission: RolePermission,
    state: RolePermission["lifecycle_state"],
  ) => {
    setSaving(true);
    setError(null);
    try {
      const preview = await previewPermissionLifecycle(permission.id, state);
      const confirmed = window.confirm(
        `${permission.code}: ${preview.affected_roles} rol ve ${preview.affected_users} kullanıcı etkilenecek. Devam edilsin mi?`,
      );
      if (!confirmed) return;
      await updatePermissionLifecycle(
        permission.id,
        state,
        state === "active" ? undefined : "Platform yöneticisi tarafından değiştirildi",
      );
      await Promise.all([loadContext(), loadOrganization()]);
      setSuccess(`İzin durumu “${state}” olarak güncellendi.`);
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
          <button className="btn primary" onClick={openCreateRole} disabled={!organizationId || saving || !canCreateRole}>
            Yeni Rol
          </button>
        ) : undefined}
      />

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <section className="role-scope-card card" aria-label="Rol kapsamı">
        <label className="form-field role-organization-field">
          <span className="form-label">Organizasyon</span>
          <select
            className="input"
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
          >
            <option value="">Organizasyon seçin</option>
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>{organization.name}</option>
            ))}
          </select>
        </label>
        <div className="role-summary-grid" aria-label="Rol özeti">
          <div><strong>{roles.length}</strong><span>Atanabilir rol</span></div>
          <div><strong>{roles.filter((role) => !role.is_protected).length}</strong><span>Düzenlenebilir rol</span></div>
          <div><strong>{permissions.filter((item) => item.lifecycle_state === "active").length}</strong><span>Aktif izin</span></div>
        </div>
      </section>

      <Tabs items={tabs} active={tab} onChange={setTab} ariaLabel="Rol yönetimi bölümleri" />

      <TabPanel id="panel-organization" labelledBy="tab-organization" active={tab === "organization"}>
        <div className="section-header role-section-header">
          <div>
            <h2 className="section-title">{selectedOrganization?.name ?? "Organizasyon"} rolleri</h2>
            <p className="section-description muted">
              Kullanıcılar bu organizasyonda aşağıdaki rollerden birine atanabilir.
            </p>
          </div>
        </div>
        {organizationLoading ? <LoadingState message="Organizasyon rolleri yükleniyor…" /> : (
          <div className="role-card-grid">
            {roles.map((role) => {
              const isExpanded = expandedRoles.has(role.id);
              const sourceTemplate = templates.find((item) => item.id === role.source_template_role_id);
              const isOutdated = Boolean(
                sourceTemplate
                && role.source_template_version !== null
                && role.source_template_version < sourceTemplate.template_version,
              );
              return (
                <article className={`role-card card ${role.is_protected ? "role-card-protected" : ""}`} key={role.id}>
                  <div className="role-card-topline">
                    <div className="role-card-title">
                      <span className={`role-kind-icon ${role.is_protected ? "protected" : "custom"}`} aria-hidden="true">
                        {role.is_protected ? "◆" : "◇"}
                      </span>
                      <div>
                        <h3>{role.name}</h3>
                        <code>{role.slug}</code>
                      </div>
                    </div>
                    <span className={`badge ${role.is_protected ? "badge-primary" : role.source_template_role_id ? "badge-info" : "badge-neutral"}`}>
                      {role.is_protected ? "Sistem rolü" : role.source_template_role_id ? "Şablondan türetildi" : "Özel rol"}
                    </span>
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
                    {role.source_template_role_id ? (
                      <div><strong>{role.permissions_customized ? "Özel" : "Standart"}</strong><span>izin seti</span></div>
                    ) : null}
                  </div>

                  {isExpanded ? <RolePermissionPreview role={role} permissions={permissions} /> : null}

                  <footer className="role-card-actions">
                    <button
                      type="button"
                      className="btn secondary btn-sm"
                      onClick={() => setExpandedRoles((current) => {
                        const next = new Set(current);
                        if (next.has(role.id)) next.delete(role.id);
                        else next.add(role.id);
                        return next;
                      })}
                    >
                      {isExpanded ? "İzinleri gizle" : "İzinleri göster"}
                    </button>
                    {!role.is_protected ? (
                      <>
                        {canUpdateRole ? (
                          <button
                            type="button"
                            className="btn secondary btn-sm"
                            onClick={() => {
                              setEditing(role);
                              setForm({ name: role.name, slug: role.slug, permissionIds: role.permission_ids });
                            }}
                          >
                            Düzenle
                          </button>
                        ) : null}
                        {role.source_template_role_id && isSuperAdmin ? (
                          <button type="button" className="btn secondary btn-sm" onClick={() => void sync(role)} disabled={saving}>
                            Şablondan güncelle
                          </button>
                        ) : null}
                        {canDeleteRole ? (
                          <button type="button" className="btn danger btn-sm" onClick={() => setDeleteTarget(role)}>
                            Sil
                          </button>
                        ) : null}
                      </>
                    ) : null}
                  </footer>
                </article>
              );
            })}
            {!roles.length ? (
              <EmptyState
                title="Bu organizasyonda atanabilir rol yok"
                description="Özel rol oluşturun veya varsayılan bir şablondan rol türetin."
                actionLabel={canCreateRole ? "Yeni Rol" : undefined}
                onAction={canCreateRole ? openCreateRole : undefined}
              />
            ) : null}
          </div>
        )}
      </TabPanel>

      <TabPanel id="panel-templates" labelledBy="tab-templates" active={tab === "templates"}>
        <div className="section-header role-section-header">
          <div>
            <h2 className="section-title">Varsayılan rol şablonları</h2>
            <p className="section-description muted">
              Şablon değişiklikleri yeni türetilecek rollere uygulanır. Mevcut roller ayrıca senkronize edilmelidir.
            </p>
          </div>
        </div>
        <div className="template-list">
          {templates.map((template) => {
            const draft = templateDrafts[template.id] ?? template.permission_ids;
            const hasChanges = !samePermissionIds(draft, template.permission_ids);
            return (
              <article className="template-card card" key={template.id}>
                <header className="template-card-header">
                  <div>
                    <div className="template-title-row">
                      <h3>{template.name}</h3>
                      <span className="badge badge-info">Şablon</span>
                    </div>
                    <p>
                      <code>{template.slug}</code> · Sürüm {template.template_version} · Doğrudan kullanıcıya atanamaz
                    </p>
                  </div>
                  <div className="template-actions">
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={() => {
                        setDeriveSource(template);
                        setForm({
                          ...EMPTY_ROLE,
                          name: template.name,
                          slug: `${template.slug}_${selectedOrganization?.slug ?? organizationId.slice(0, 6)}`,
                        });
                      }}
                      disabled={!organizationId || saving}
                    >
                      Organizasyona ata
                    </button>
                    <button
                      type="button"
                      className="btn primary"
                      onClick={() => void saveTemplate(template)}
                      disabled={!hasChanges || saving}
                    >
                      {hasChanges ? "Şablonu Kaydet" : "Değişiklik Yok"}
                    </button>
                  </div>
                </header>
                {hasChanges ? (
                  <Banner variant="info">Kaydedilmemiş izin değişiklikleri var.</Banner>
                ) : null}
                <PermissionMatrix
                  permissions={permissions.filter((item) => item.lifecycle_state === "active")}
                  selected={draft}
                  disabled={saving}
                  onChange={(ids) => setTemplateDrafts((current) => ({ ...current, [template.id]: ids }))}
                />
              </article>
            );
          })}
        </div>
      </TabPanel>

      <TabPanel id="panel-permissions" labelledBy="tab-permissions" active={tab === "permissions"}>
        <div className="permission-lifecycle-notice card">
          <strong>Global etki alanı</strong>
          <p>
            Bir izni kilitlemek veya devre dışı bırakmak, OrganizationAdmin dahil tüm rollerden kaldırır.
            Super Admin erişimi etkilenmez.
          </p>
        </div>
        <div className="permission-lifecycle-toolbar">
          <input
            className="input"
            value={permissionQuery}
            onChange={(event) => setPermissionQuery(event.target.value)}
            placeholder="İzin ara…"
            aria-label="Global izin ara"
          />
          <select
            className="input"
            value={lifecycleFilter}
            onChange={(event) => setLifecycleFilter(event.target.value as LifecycleFilter)}
            aria-label="İzin durumu"
          >
            <option value="all">Tüm durumlar</option>
            <option value="active">Aktif</option>
            <option value="locked">Kilitli</option>
            <option value="inactive">Devre dışı</option>
          </select>
        </div>
        <div className="permission-lifecycle-list">
          {filteredPermissions.map((permission) => (
            <article className="permission-lifecycle-row card" key={permission.id}>
              <div className="permission-lifecycle-copy">
                <div>
                  <code>{permission.code}</code>
                  <span className={`badge ${permission.lifecycle_state === "active" ? "badge-success" : permission.lifecycle_state === "locked" ? "badge-warning" : "badge-danger"}`}>
                    {permission.lifecycle_state === "active" ? "Aktif" : permission.lifecycle_state === "locked" ? "Kilitli" : "Devre dışı"}
                  </span>
                  {!permission.is_assignable ? <span className="badge badge-neutral">Platform yönetimli</span> : null}
                </div>
                <p>{permission.description}</p>
              </div>
              <div className="permission-lifecycle-actions">
                {permission.lifecycle_state === "active" ? (
                  <>
                    <button className="btn secondary btn-sm" disabled={saving} onClick={() => void changePermissionState(permission, "locked")}>Kilitle</button>
                    <button className="btn danger btn-sm" disabled={saving} onClick={() => void changePermissionState(permission, "inactive")}>Devre dışı bırak</button>
                  </>
                ) : (
                  <button className="btn secondary btn-sm" disabled={saving} onClick={() => void changePermissionState(permission, "active")}>Aktifleştir</button>
                )}
              </div>
            </article>
          ))}
          {!filteredPermissions.length ? (
            <EmptyState title="İzin bulunamadı" description="Arama veya durum filtresini değiştirin." />
          ) : null}
        </div>
      </TabPanel>

      {editing !== undefined ? (
        <FormModal
          title={editing ? "Rolü Düzenle" : "Yeni Rol"}
          onClose={() => !saving && setEditing(undefined)}
          formWidth="wide"
        >
          <form className="crm-form-stack" onSubmit={saveRole}>
            <div className="role-form-grid">
              <label className="form-field">
                <span className="form-label">Rol adı *</span>
                <input
                  className="input"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({
                    ...current,
                    name: event.target.value,
                    ...(!editing ? { slug: slugify(event.target.value) } : {}),
                  }))}
                  required
                />
              </label>
              <label className="form-field">
                <span className="form-label">Rol kodu *</span>
                <input
                  className="input"
                  value={form.slug}
                  onChange={(event) => setForm((current) => ({ ...current, slug: slugify(event.target.value) }))}
                  required
                />
              </label>
            </div>
            <PermissionMatrix
              permissions={permissions.filter((item) => item.lifecycle_state === "active" && item.is_assignable)}
              selected={form.permissionIds}
              disabled={saving}
              onChange={(ids) => setForm((current) => ({ ...current, permissionIds: ids }))}
            />
            <div className="form-actions">
              <button type="button" className="btn secondary" onClick={() => setEditing(undefined)} disabled={saving}>Vazgeç</button>
              <button className="btn primary" disabled={saving || !form.name.trim() || !form.slug}>Kaydet</button>
            </div>
          </form>
        </FormModal>
      ) : null}

      {deriveSource ? (
        <FormModal title={`${deriveSource.name} şablonundan rol oluştur`} onClose={() => !saving && setDeriveSource(null)}>
          <form className="crm-form-stack" onSubmit={derive}>
            <Banner variant="info">
              Rol, {selectedOrganization?.name ?? "seçili organizasyon"} organizasyonuna atanacak ve şablonun mevcut izinlerini alacak.
            </Banner>
            <label className="form-field">
              <span className="form-label">Rol adı *</span>
              <input className="input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
            </label>
            <label className="form-field">
              <span className="form-label">Rol kodu *</span>
              <input className="input" value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: slugify(event.target.value) }))} required />
            </label>
            <div className="form-actions">
              <button type="button" className="btn secondary" onClick={() => setDeriveSource(null)} disabled={saving}>Vazgeç</button>
              <button className="btn primary" disabled={saving || !form.name.trim() || !form.slug}>Rolü Oluştur</button>
            </div>
          </form>
        </FormModal>
      ) : null}

      {deleteTarget ? (
        <ConfirmDialog
          title="Rolü Sil"
          message={`${deleteTarget.name} rolü silinecek. Aktif kullanıcıya atanmışsa işlem güvenlik nedeniyle engellenir.`}
          confirmLabel="Rolü Sil"
          variant="danger"
          loading={saving}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => {
            if (!organizationId) return;
            setSaving(true);
            setError(null);
            void deleteOrganizationRole(organizationId, deleteTarget.id)
              .then(async () => {
                setDeleteTarget(null);
                setSuccess("Rol silindi.");
                await loadOrganization();
              })
              .catch((err) => setError(errorMessage(err)))
              .finally(() => setSaving(false));
          }}
        />
      ) : null}
    </PageShell>
  );
}
