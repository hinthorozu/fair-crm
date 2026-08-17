import React from "react";

import { ApiError } from "../api/client";
import {
  createManagedUser,
  deleteManagedUser,
  getUserManagementContext,
  listAssignableRoles,
  listDeletedManagedUsers,
  listManagedUsers,
  restoreManagedUser,
  updateManagedUser,
  type AssignableRole,
  type ManagedOrganization,
  type ManagedUser,
} from "../api/userManagement";
import { NavIconEye, NavIconEyeOff } from "../components/layout/NavIcons";
import { Banner } from "../components/ui/Banner";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  UniversalDataTable,
  type UniversalDataTableColumn,
} from "../components/ui/UniversalDataTable";
import { getGrantedCorePermissions } from "../permissions/corePermissions";
import {
  PERMISSION_USERS_CREATE,
  PERMISSION_USERS_DELETE,
  PERMISSION_USERS_UPDATE,
} from "../permissions/navigationPermissions";

interface UserFormState {
  email: string;
  password: string;
  roleId: string;
  status: "active" | "inactive";
  isSuperAdmin: boolean;
}

const EMPTY_FORM: UserFormState = {
  email: "",
  password: "",
  roleId: "",
  status: "active",
  isSuperAdmin: false,
};

export function UsersAdminPage() {
  const [organizations, setOrganizations] = React.useState<ManagedOrganization[]>([]);
  const [organizationId, setOrganizationId] = React.useState("");
  const [actorIsSuperAdmin, setActorIsSuperAdmin] = React.useState(false);
  const [users, setUsers] = React.useState<ManagedUser[]>([]);
  const [deletedUsers, setDeletedUsers] = React.useState<ManagedUser[]>([]);
  const [canRestoreDeletedUsers, setCanRestoreDeletedUsers] = React.useState(false);
  const [restoringUserId, setRestoringUserId] = React.useState<string | null>(null);
  const [roles, setRoles] = React.useState<AssignableRole[]>([]);
  const [canManageSuperAdmin, setCanManageSuperAdmin] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<ManagedUser | null | undefined>(undefined);
  const [form, setForm] = React.useState<UserFormState>(EMPTY_FORM);
  const [showPassword, setShowPassword] = React.useState(true);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<ManagedUser | null>(null);
  const [deleting, setDeleting] = React.useState(false);
  const grantedPermissions = getGrantedCorePermissions();
  const canCreateUsers = actorIsSuperAdmin || grantedPermissions.has(PERMISSION_USERS_CREATE);
  const canUpdateUsers = actorIsSuperAdmin || grantedPermissions.has(PERMISSION_USERS_UPDATE);
  const canDeleteUsers = actorIsSuperAdmin || grantedPermissions.has(PERMISSION_USERS_DELETE);
  const canRestoreUsers = canUpdateUsers && canRestoreDeletedUsers;

  React.useEffect(() => {
    let active = true;
    const loadContext = async () => {
      try {
        const context = await getUserManagementContext();
        if (!active) return;
        setActorIsSuperAdmin(context.is_super_admin);
        setOrganizations(context.organizations);
        setOrganizationId(context.organizations[0]?.id ?? "");
      } catch (err) {
        if (active) setError(err instanceof ApiError ? err.message : "Organizasyon bilgisi yüklenemedi.");
      }
    };
    void loadContext();
    return () => { active = false; };
  }, []);

  const loadUsers = React.useCallback(async () => {
    if (!organizationId) {
      setUsers([]);
      setDeletedUsers([]);
      setCanRestoreDeletedUsers(false);
      setRoles([]);
      setCanManageSuperAdmin(false);
      setLoading(false);
      return;
    }
    setLoading(true); setError(null);
    try {
      const [userResult, roleResult] = await Promise.all([
        listManagedUsers(organizationId),
        listAssignableRoles(organizationId),
      ]);
      setUsers(userResult.items);
      setCanManageSuperAdmin(userResult.can_manage_super_admin);
      setRoles(roleResult);

      if (!canUpdateUsers) {
        setDeletedUsers([]);
        setCanRestoreDeletedUsers(false);
      } else {
        try {
          const deletedResult = await listDeletedManagedUsers(organizationId);
          setDeletedUsers(deletedResult.items);
          setCanRestoreDeletedUsers(true);
        } catch (err) {
          if (err instanceof ApiError && err.status === 403) {
            setDeletedUsers([]);
            setCanRestoreDeletedUsers(false);
          } else {
            throw err;
          }
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kullanıcılar yüklenemedi.");
    } finally { setLoading(false); }
  }, [canUpdateUsers, organizationId]);

  React.useEffect(() => { void loadUsers(); }, [loadUsers]);

  const changeOrganization = (nextOrganizationId: string) => {
    setOrganizationId(nextOrganizationId);
    setForm((current) => ({ ...current, roleId: "" }));
  };

  const openCreate = () => {
    if (!canCreateUsers) return;
    setEditing(null);
    setForm({ ...EMPTY_FORM, roleId: roles[0]?.id ?? "" });
    setShowPassword(true);
    setFormError(null);
  };

  const openEdit = (user: ManagedUser) => {
    if (!canUpdateUsers) return;
    setEditing(user);
    setForm({ email: user.email, password: "", roleId: user.role?.id ?? roles[0]?.id ?? "", status: user.status === "inactive" ? "inactive" : "active", isSuperAdmin: Boolean(user.is_super_admin) });
    setShowPassword(true); setFormError(null);
  };

  const closeForm = () => { if (saving) return; setEditing(undefined); setFormError(null); };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (editing ? !canUpdateUsers : !canCreateUsers) return;
    if (!organizationId) { setFormError("Organizasyon seçimi zorunludur."); return; }
    if (!form.email.trim()) { setFormError("E-posta zorunludur."); return; }
    if (!form.isSuperAdmin && !form.roleId) { setFormError("Rol seçimi zorunludur."); return; }
    if (!editing && !form.password) { setFormError("Şifre zorunludur."); return; }
    setSaving(true); setFormError(null); setSuccess(null);
    try {
      if (editing) {
        await updateManagedUser(organizationId, editing.id, { email: form.email.trim(), role_id: form.roleId, status: form.status, ...(form.password ? { password: form.password } : {}), ...(canManageSuperAdmin ? { is_super_admin: form.isSuperAdmin } : {}) });
        setSuccess("Kullanıcı güncellendi.");
      } else {
        await createManagedUser(organizationId, { email: form.email.trim(), password: form.password, ...(form.roleId ? { role_id: form.roleId } : {}), status: form.status, ...(canManageSuperAdmin ? { is_super_admin: form.isSuperAdmin } : {}) });
        setSuccess("Kullanıcı oluşturuldu.");
      }
      setEditing(undefined); await loadUsers();
    } catch (err) { setFormError(err instanceof ApiError ? err.message : "Kullanıcı kaydedilemedi."); }
    finally { setSaving(false); }
  };

  const confirmDelete = async () => {
    if (!canDeleteUsers || !deleteTarget || !organizationId) return;
    setDeleting(true); setError(null);
    try { await deleteManagedUser(organizationId, deleteTarget.id); setDeleteTarget(null); setSuccess("Kullanıcı silindi."); await loadUsers(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Kullanıcı silinemedi."); setDeleteTarget(null); }
    finally { setDeleting(false); }
  };

  const restoreDeletedUser = async (user: ManagedUser) => {
    if (!canRestoreUsers || !organizationId || restoringUserId) return;
    setRestoringUserId(user.id); setError(null); setSuccess(null);
    try {
      await restoreManagedUser(organizationId, user.id);
      setSuccess(`${user.email} kullanıcısı geri alındı.`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kullanıcı geri alınamadı.");
    } finally {
      setRestoringUserId(null);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<ManagedUser>[]>(() => [
    { key: "email", title: "E-posta", render: (user) => <strong>{user.email}</strong> },
    { key: "role", title: "Rol", render: (user) => user.role?.name ?? "—" },
    { key: "status", title: "Durum", render: (user) => user.status === "active" ? "Aktif" : "Pasif" },
    ...(canManageSuperAdmin ? [{ key: "super-admin", title: "Super Admin", render: (user: ManagedUser) => user.is_super_admin ? "Evet" : "Hayır" } as UniversalDataTableColumn<ManagedUser>] : []),
    ...(canUpdateUsers || canDeleteUsers ? [{ key: "actions", title: "İşlemler", sortable: false, className: "col-actions", render: (user: ManagedUser) => <TableRowActions>{canUpdateUsers ? <button type="button" className="btn link" onClick={() => openEdit(user)}>Düzenle</button> : null}{canDeleteUsers ? <button type="button" className="btn link danger" onClick={() => setDeleteTarget(user)}>Sil</button> : null}</TableRowActions> } as UniversalDataTableColumn<ManagedUser>] : []),
  ], [canDeleteUsers, canManageSuperAdmin, canUpdateUsers, roles]);

  const deletedColumns = React.useMemo<UniversalDataTableColumn<ManagedUser>[]>(() => [
    { key: "email", title: "E-posta", render: (user) => <strong>{user.email}</strong> },
    { key: "role", title: "Son Rol", render: (user) => user.role?.name ?? "—" },
    { key: "status", title: "Durum", render: () => "Silindi" },
    ...(canRestoreUsers ? [{ key: "actions", title: "İşlemler", sortable: false, className: "col-actions", render: (user: ManagedUser) => <TableRowActions><button type="button" className="btn link" disabled={restoringUserId !== null} onClick={() => void restoreDeletedUser(user)}>{restoringUserId === user.id ? "Geri alınıyor…" : "Geri Al"}</button></TableRowActions> } as UniversalDataTableColumn<ManagedUser>] : []),
  ], [canRestoreUsers, organizationId, restoringUserId]);

  const formOpen = editing !== undefined;
  const selectedOrganization = organizations.find((item) => item.id === organizationId) ?? null;

  const organizationField = actorIsSuperAdmin ? (
    <label className="form-field">
      <span className="form-label">Organizasyon *</span>
      <select className="input" value={organizationId} onChange={(event) => changeOrganization(event.target.value)} disabled={saving || Boolean(editing)} required>
        <option value="">Organizasyon seçin</option>
        {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
      </select>
    </label>
  ) : (
    <div className="form-field"><span className="form-label">Organizasyon</span><strong>{selectedOrganization?.name ?? "Organizasyon bulunamadı"}</strong></div>
  );

  const canOfferCreate = canCreateUsers && Boolean(organizationId) && roles.length > 0;

  return <PageShell>
    <PageHeader title="Kullanıcılar" actions={canCreateUsers ? <button type="button" className="btn primary" onClick={openCreate} disabled={!canOfferCreate}>Yeni Kullanıcı</button> : undefined} />
    {success ? <Banner variant="success">{success}</Banner> : null}
    {error ? <Banner variant="error">{error}</Banner> : null}
    <div className="card" style={{ marginBottom: 16, padding: 16 }}>{actorIsSuperAdmin ? <label className="form-field"><span className="form-label">Organizasyon</span><select className="input" value={organizationId} onChange={(event) => changeOrganization(event.target.value)}><option value="">Organizasyon seçin</option>{organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label> : <div className="form-field"><span className="form-label">Organizasyon</span><strong>{selectedOrganization?.name ?? "Organizasyon bulunamadı"}</strong></div>}</div>
    <UniversalDataTable items={users} columns={columns} rowKey={(user) => user.id} loading={loading} error={error} onRetry={() => void loadUsers()} emptyState={<EmptyState title="Kullanıcı bulunamadı" actionLabel={canOfferCreate ? "Yeni Kullanıcı" : undefined} onAction={canOfferCreate ? openCreate : undefined} />} />
    {canRestoreUsers ? <div style={{ marginTop: 24 }}><h3>Silinen Kullanıcılar</h3><UniversalDataTable items={deletedUsers} columns={deletedColumns} rowKey={(user) => user.id} loading={loading} emptyState={<EmptyState title="Silinen kullanıcı bulunamadı" />} /></div> : null}
    {formOpen ? <FormModal title={editing ? "Kullanıcıyı Düzenle" : "Yeni Kullanıcı"} onClose={closeForm} formWidth="standard"><form onSubmit={submit} className="crm-form-stack">
      {formError ? <Banner variant="error">{formError}</Banner> : null}
      {organizationField}
      <label className="form-field"><span className="form-label">E-posta *</span><input className="input" type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} required disabled={saving} /></label>
      <label className="form-field"><span className="form-label">Şifre{editing ? "" : " *"}</span><span style={{ position: "relative", display: "block" }}><input className="input" type={showPassword ? "text" : "password"} value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} required={!editing} disabled={saving} autoComplete="new-password" style={{ width: "100%", paddingRight: 44 }} /><button type="button" onClick={() => setShowPassword((current) => !current)} disabled={saving} aria-label={showPassword ? "Şifreyi gizle" : "Şifreyi göster"} title={showPassword ? "Şifreyi gizle" : "Şifreyi göster"} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", display: "inline-flex", alignItems: "center", justifyContent: "center", padding: 0, border: 0, background: "transparent", color: "inherit", cursor: "pointer" }}>{showPassword ? <NavIconEyeOff /> : <NavIconEye />}</button></span>{editing ? <span className="form-hint">Değiştirmeyecekseniz boş bırakın.</span> : null}</label>
      <label className="form-field"><span className="form-label">Rol{form.isSuperAdmin ? "" : " *"}</span><select className="input" value={form.roleId} onChange={(event) => setForm((current) => ({ ...current, roleId: event.target.value }))} required={!form.isSuperAdmin} disabled={saving || form.isSuperAdmin}><option value="">{form.isSuperAdmin ? "Super Admin rol kullanmaz" : "Rol seçin"}</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></label>
      <label className="form-field"><span className="form-label">Durum</span><select className="input" value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as "active" | "inactive" }))} disabled={saving}><option value="active">Aktif</option><option value="inactive">Pasif</option></select></label>
      {canManageSuperAdmin ? <label className="form-field"><span className="form-label">Super Admin</span><input type="checkbox" checked={form.isSuperAdmin} onChange={(event) => setForm((current) => ({ ...current, isSuperAdmin: event.target.checked, roleId: event.target.checked ? "" : current.roleId }))} disabled={saving} /></label> : null}
      <div className="form-actions"><button type="button" className="btn secondary" onClick={closeForm} disabled={saving}>Vazgeç</button><button type="submit" className="btn primary" disabled={saving}>{saving ? "Kaydediliyor…" : "Kaydet"}</button></div>
    </form></FormModal> : null}
    {deleteTarget && canDeleteUsers ? <ConfirmDialog title="Kullanıcıyı Sil" message={`${deleteTarget.email} kullanıcısı bu organizasyondan kaldırılacak.`} confirmLabel="Sil" variant="danger" loading={deleting} onCancel={() => setDeleteTarget(null)} onConfirm={() => void confirmDelete()} /> : null}
  </PageShell>;
}