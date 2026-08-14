import React from "react";

import { ApiError } from "../api/client";
import {
  createOrganizationRole, deleteOrganizationRole, deriveRoleTemplate,
  listManagedRoles, listPlatformPermissions, listRolePermissions, listRoleTemplates,
  previewPermissionLifecycle, previewTemplateSync, syncRoleTemplate, updateOrganizationRole,
  updateOrganizationRolePermissions, updatePermissionLifecycle, updateRoleTemplate,
  type ManagedRole, type RolePermission,
} from "../api/roleManagement";
import { getUserManagementContext, type ManagedOrganization } from "../api/userManagement";
import { Banner } from "../components/ui/Banner";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";

type Tab = "organization" | "templates" | "permissions";
interface RoleForm { name: string; slug: string; permissionIds: string[] }
const EMPTY_ROLE: RoleForm = { name: "", slug: "", permissionIds: [] };
const errorMessage = (error: unknown) => error instanceof ApiError ? error.message : "İşlem tamamlanamadı.";

function PermissionMatrix({ permissions, selected, disabled, onChange }: {
  permissions: RolePermission[]; selected: string[]; disabled?: boolean; onChange: (ids: string[]) => void;
}) {
  const groups = React.useMemo(() => {
    const result = new Map<string, RolePermission[]>();
    permissions.forEach((permission) => {
      const group = permission.code.split(".").slice(0, 2).join(".");
      result.set(group, [...(result.get(group) ?? []), permission]);
    });
    return [...result.entries()];
  }, [permissions]);
  return <div style={{ display: "grid", gap: 12, maxHeight: 420, overflow: "auto" }}>
    {groups.map(([group, items]) => <section className="card" style={{ padding: 12 }} key={group}>
      <strong>{group}</strong><div style={{ display: "grid", gap: 8, marginTop: 8 }}>
        {items.map((permission) => <label key={permission.id} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <input type="checkbox" checked={selected.includes(permission.id)} disabled={disabled || permission.lifecycle_state !== "active"} onChange={(event) => onChange(event.target.checked ? [...selected, permission.id] : selected.filter((id) => id !== permission.id))} />
          <span><code>{permission.code}</code><br /><small>{permission.description}</small></span>
        </label>)}
      </div>
    </section>)}
  </div>;
}

export function RoleManagementPage() {
  const [tab, setTab] = React.useState<Tab>("organization");
  const [isSuperAdmin, setIsSuperAdmin] = React.useState(false);
  const [organizations, setOrganizations] = React.useState<ManagedOrganization[]>([]);
  const [organizationId, setOrganizationId] = React.useState("");
  const [roles, setRoles] = React.useState<ManagedRole[]>([]);
  const [templates, setTemplates] = React.useState<ManagedRole[]>([]);
  const [permissions, setPermissions] = React.useState<RolePermission[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<ManagedRole | null | undefined>(undefined);
  const [form, setForm] = React.useState<RoleForm>(EMPTY_ROLE);
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<ManagedRole | null>(null);
  const [deriveSource, setDeriveSource] = React.useState<ManagedRole | null>(null);

  const loadContext = React.useCallback(async () => {
    const context = await getUserManagementContext();
    setIsSuperAdmin(context.is_super_admin); setOrganizations(context.organizations);
    setOrganizationId((current) => current || context.organizations[0]?.id || "");
    if (context.is_super_admin) {
      const [templateResult, permissionResult] = await Promise.all([listRoleTemplates(), listPlatformPermissions()]);
      setTemplates(templateResult); setPermissions(permissionResult);
    }
  }, []);
  const loadOrganization = React.useCallback(async () => {
    if (!organizationId) { setRoles([]); return; }
    const [roleResult, permissionResult] = await Promise.all([listManagedRoles(organizationId), isSuperAdmin ? listPlatformPermissions() : listRolePermissions(organizationId)]);
    setRoles(roleResult); setPermissions(permissionResult);
  }, [organizationId, isSuperAdmin]);
  React.useEffect(() => { setLoading(true); loadContext().catch((err) => setError(errorMessage(err))).finally(() => setLoading(false)); }, [loadContext]);
  React.useEffect(() => { loadOrganization().catch((err) => setError(errorMessage(err))); }, [loadOrganization]);

  const saveRole = async (event: React.FormEvent) => {
    event.preventDefault(); if (!organizationId) return; setSaving(true); setError(null);
    try {
      if (editing) {
        await updateOrganizationRole(organizationId, editing.id, { name: form.name, slug: form.slug });
        await updateOrganizationRolePermissions(organizationId, editing.id, form.permissionIds);
      } else await createOrganizationRole(organizationId, { name: form.name, slug: form.slug, permission_ids: form.permissionIds });
      setSuccess(editing ? "Rol güncellendi." : "Rol oluşturuldu."); setEditing(undefined); await loadOrganization();
    } catch (err) { setError(errorMessage(err)); } finally { setSaving(false); }
  };
  const saveTemplate = async (template: ManagedRole, permissionIds: string[]) => {
    setSaving(true); setError(null);
    try { await updateRoleTemplate(template.id, permissionIds); setTemplates(await listRoleTemplates()); setSuccess("Şablon güncellendi. Mevcut roller otomatik değiştirilmedi."); }
    catch (err) { setError(errorMessage(err)); } finally { setSaving(false); }
  };
  const derive = async (event: React.FormEvent) => {
    event.preventDefault(); if (!deriveSource || !organizationId) return; setSaving(true);
    try { await deriveRoleTemplate(deriveSource.id, { organization_id: organizationId, name: form.name, slug: form.slug }); setDeriveSource(null); setSuccess("Şablondan rol oluşturuldu."); await loadOrganization(); }
    catch (err) { setError(errorMessage(err)); } finally { setSaving(false); }
  };
  const sync = async (role: ManagedRole) => {
    if (!role.source_template_role_id) return; setSaving(true); setError(null);
    try {
      const preview = (await previewTemplateSync(role.source_template_role_id, [role.id]))[0];
      if (!preview || !window.confirm(`${role.name}: ${preview.add_count} izin eklenecek, ${preview.remove_count} izin kaldırılacak. Devam edilsin mi?`)) return;
      await syncRoleTemplate(role.source_template_role_id, [role.id]); setSuccess("Rol şablonla birebir eşitlendi."); await loadOrganization();
    } catch (err) { setError(errorMessage(err)); } finally { setSaving(false); }
  };
  const changePermissionState = async (permission: RolePermission, state: RolePermission["lifecycle_state"]) => {
    setSaving(true); setError(null);
    try {
      const preview = await previewPermissionLifecycle(permission.id, state);
      if (!window.confirm(`${permission.code}: ${preview.affected_roles} rol ve ${preview.affected_users} kullanıcı etkilenecek. Devam edilsin mi?`)) return;
      await updatePermissionLifecycle(permission.id, state, state === "active" ? undefined : "Platform yöneticisi tarafından değiştirildi");
      await loadContext(); setSuccess(`İzin durumu ${state} olarak güncellendi.`);
    } catch (err) { setError(errorMessage(err)); } finally { setSaving(false); }
  };

  if (loading) return <PageShell><PageHeader title="Roller ve Yetkiler" /><p>Yükleniyor…</p></PageShell>;
  return <PageShell>
    <PageHeader title="Roller ve Yetkiler" actions={tab === "organization" ? <button className="btn primary" onClick={() => { setEditing(null); setForm(EMPTY_ROLE); }} disabled={!organizationId}>Yeni Rol</button> : undefined} />
    {success ? <Banner variant="success">{success}</Banner> : null}{error ? <Banner variant="error">{error}</Banner> : null}
    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}><button className={`btn ${tab === "organization" ? "primary" : "secondary"}`} onClick={() => setTab("organization")}>Organizasyon Rolleri</button>{isSuperAdmin ? <><button className={`btn ${tab === "templates" ? "primary" : "secondary"}`} onClick={() => setTab("templates")}>Varsayılan Şablonlar</button><button className={`btn ${tab === "permissions" ? "primary" : "secondary"}`} onClick={() => setTab("permissions")}>İzin Kilitleri</button></> : null}</div>
    <label className="form-field" style={{ marginBottom: 16 }}><span className="form-label">Organizasyon</span><select className="input" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}><option value="">Organizasyon seçin</option>{organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label>
    {tab === "organization" ? <div style={{ display: "grid", gap: 12 }}>{roles.map((role) => <div className="card" style={{ padding: 16 }} key={role.id}><div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}><div><strong>{role.name}</strong> <code>{role.slug}</code><br /><small>{role.is_protected ? "Değiştirilemez sistem rolü" : role.source_template_role_id ? `Şablondan türetildi · sürüm ${role.source_template_version ?? "—"}` : "Özel rol"} · {role.permission_ids.length} izin</small></div>{!role.is_protected ? <div style={{ display: "flex", gap: 8 }}><button className="btn secondary" onClick={() => { setEditing(role); setForm({ name: role.name, slug: role.slug, permissionIds: role.permission_ids }); }}>Düzenle</button>{role.source_template_role_id ? <button className="btn secondary" onClick={() => void sync(role)}>Şablondan güncelle</button> : null}<button className="btn danger" onClick={() => setDeleteTarget(role)}>Sil</button></div> : null}</div></div>)}{!roles.length ? <p>Bu organizasyonda atanabilir rol bulunamadı.</p> : null}</div> : null}
    {tab === "templates" ? <div style={{ display: "grid", gap: 16 }}>{templates.map((template) => <div className="card" style={{ padding: 16 }} key={template.id}><div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}><div><strong>{template.name}</strong><br /><small>Sürüm {template.template_version} · Doğrudan atanamaz</small></div><button className="btn primary" onClick={() => { setDeriveSource(template); setForm({ ...EMPTY_ROLE, name: template.name, slug: `${template.slug}_${organizationId.slice(0, 6)}` }); }} disabled={!organizationId}>Organizasyona türet</button></div><PermissionMatrix permissions={permissions.filter((item) => item.lifecycle_state === "active")} selected={template.permission_ids} disabled={saving} onChange={(ids) => void saveTemplate(template, ids)} /></div>)}</div> : null}
    {tab === "permissions" ? <div style={{ display: "grid", gap: 8 }}>{permissions.map((permission) => <div className="card" style={{ padding: 12, display: "flex", justifyContent: "space-between", gap: 12 }} key={permission.id}><div><code>{permission.code}</code><br /><small>{permission.description} · {permission.lifecycle_state}</small></div>{permission.lifecycle_state === "active" ? <div style={{ display: "flex", gap: 8 }}><button className="btn secondary" disabled={saving} onClick={() => void changePermissionState(permission, "locked")}>Kilitle</button><button className="btn danger" disabled={saving} onClick={() => void changePermissionState(permission, "inactive")}>Devre dışı bırak</button></div> : <button className="btn secondary" disabled={saving} onClick={() => void changePermissionState(permission, "active")}>Aktifleştir</button>}</div>)}</div> : null}
    {editing !== undefined ? <FormModal title={editing ? "Rolü Düzenle" : "Yeni Rol"} onClose={() => !saving && setEditing(undefined)} formWidth="wide"><form className="crm-form-stack" onSubmit={saveRole}><label className="form-field"><span className="form-label">Ad *</span><input className="input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required /></label><label className="form-field"><span className="form-label">Kod *</span><input className="input" value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, "_") }))} required /></label><PermissionMatrix permissions={permissions.filter((item) => item.lifecycle_state === "active" && item.is_assignable)} selected={form.permissionIds} onChange={(ids) => setForm((current) => ({ ...current, permissionIds: ids }))} /><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setEditing(undefined)}>Vazgeç</button><button className="btn primary" disabled={saving}>Kaydet</button></div></form></FormModal> : null}
    {deriveSource ? <FormModal title={`${deriveSource.name} şablonundan rol oluştur`} onClose={() => setDeriveSource(null)}><form className="crm-form-stack" onSubmit={derive}><label className="form-field"><span className="form-label">Rol adı *</span><input className="input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required /></label><label className="form-field"><span className="form-label">Kod *</span><input className="input" value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, "_") }))} required /></label><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setDeriveSource(null)}>Vazgeç</button><button className="btn primary" disabled={saving}>Oluştur</button></div></form></FormModal> : null}
    {deleteTarget ? <ConfirmDialog title="Rolü Sil" message={`${deleteTarget.name} rolü silinecek. Aktif kullanıcıya atanmışsa işlem engellenir.`} confirmLabel="Sil" variant="danger" loading={saving} onCancel={() => setDeleteTarget(null)} onConfirm={() => { if (!organizationId) return; setSaving(true); void deleteOrganizationRole(organizationId, deleteTarget.id).then(async () => { setDeleteTarget(null); setSuccess("Rol silindi."); await loadOrganization(); }).catch((err) => setError(errorMessage(err))).finally(() => setSaving(false)); }} /> : null}
  </PageShell>;
}
