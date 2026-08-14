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
} from "../api/coreIdentity";
import { Badge } from "../components/ui/Badge";
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

function slugify(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("tr-TR");
}

export function OrganizationsAdminPage() {
  const [items, setItems] = React.useState<Organization[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = React.useState<Organization | null>(null);
  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [slugTouched, setSlugTouched] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Organization | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listOrganizations());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Organizasyonlar yüklenemedi.");
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
    setSlug("");
    setSlugTouched(false);
    setFormError(null);
    setModal("create");
  };

  const openEdit = (organization: Organization) => {
    setEditing(organization);
    setName(organization.name);
    setSlug(organization.slug);
    setSlugTouched(true);
    setFormError(null);
    setModal("edit");
  };

  const closeModal = () => {
    if (saving) return;
    setModal(null);
    setEditing(null);
    setFormError(null);
  };

  const handleNameChange = (value: string) => {
    setName(value);
    if (modal === "create" && !slugTouched) setSlug(slugify(value));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanSlug = slug.trim();
    if (!cleanName) {
      setFormError("Organizasyon adı zorunludur.");
      return;
    }
    if (modal === "create" && !cleanSlug) {
      setFormError("Slug zorunludur.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (modal === "edit" && editing) {
        await updateOrganization(editing.id, { name: cleanName });
        setSuccess("Organizasyon güncellendi.");
      } else {
        await createOrganization({ name: cleanName, slug: cleanSlug });
        setSuccess("Organizasyon oluşturuldu.");
      }
      setModal(null);
      setEditing(null);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Organizasyon kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteOrganization(deleteTarget.id);
      setDeleteTarget(null);
      setSuccess("Organizasyon silindi.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Organizasyon silinemedi.");
    } finally {
      setDeleting(false);
    }
  };

  const columns = React.useMemo<UniversalDataTableColumn<Organization>[]>(
    () => [
      {
        key: "name",
        title: "Organizasyon",
        render: (organization) => <strong>{organization.name}</strong>,
      },
      {
        key: "slug",
        title: "Slug",
        render: (organization) => <code>{organization.slug}</code>,
      },
      {
        key: "status",
        title: "Durum",
        render: (organization) =>
          organization.status === "active" ? (
            <Badge variant="success">Aktif</Badge>
          ) : (
            <Badge variant="neutral">{organization.status}</Badge>
          ),
      },
      {
        key: "updated_at",
        title: "Güncellendi",
        render: (organization) => formatDate(organization.updated_at),
      },
      {
        key: "actions",
        title: "İşlemler",
        sortable: false,
        render: (organization) => (
          <TableRowActions>
            <button type="button" className="btn btn-sm secondary" onClick={() => openEdit(organization)}>
              Düzenle
            </button>
            <button type="button" className="btn btn-sm danger" onClick={() => setDeleteTarget(organization)}>
              Sil
            </button>
          </TableRowActions>
        ),
      },
    ],
    [],
  );

  return (
    <PageShell className="organizations-admin-page">
      <PageHeader
        title="Organizasyonlar"
        subtitle="Kullanıcıların bağlanacağı organizasyonları yönetin."
        actions={
          <button type="button" className="btn primary" onClick={openCreate}>
            Yeni Organizasyon
          </button>
        }
      />

      {success ? <Banner variant="success">{success}</Banner> : null}
      {error ? <Banner variant="error">{error}</Banner> : null}

      <UniversalDataTable
        items={items}
        columns={columns}
        rowKey={(organization) => organization.id}
        loading={loading}
        error={error}
        onRetry={() => void load()}
        emptyState={
          error ? undefined : (
            <EmptyState
              title="Henüz organizasyon yok"
              description="İlk organizasyonu oluşturarak başlayın."
              actionLabel="Yeni Organizasyon"
              onAction={openCreate}
            />
          )
        }
      />

      {modal ? (
        <FormModal
          title={modal === "create" ? "Yeni Organizasyon" : "Organizasyonu Düzenle"}
          onClose={closeModal}
          formWidth="standard"
        >
          <form onSubmit={handleSubmit} className="crm-form-stack">
            {formError ? <Banner variant="error">{formError}</Banner> : null}
            <label className="form-field">
              <span className="form-label">Organizasyon Adı</span>
              <input
                className="input"
                value={name}
                onChange={(event) => handleNameChange(event.target.value)}
                autoFocus
                required
              />
            </label>
            <label className="form-field">
              <span className="form-label">Slug</span>
              <input
                className="input"
                value={slug}
                onChange={(event) => {
                  setSlugTouched(true);
                  setSlug(event.target.value);
                }}
                disabled={modal === "edit"}
                required={modal === "create"}
              />
              {modal === "edit" ? (
                <span className="form-hint">Slug mevcut API sözleşmesinde değiştirilemez.</span>
              ) : null}
            </label>
            <div className="form-actions">
              <button type="button" className="btn secondary" onClick={closeModal} disabled={saving}>
                Vazgeç
              </button>
              <button type="submit" className="btn primary" disabled={saving}>
                {saving ? "Kaydediliyor…" : "Kaydet"}
              </button>
            </div>
          </form>
        </FormModal>
      ) : null}

      {deleteTarget ? (
        <ConfirmDialog
          title="Organizasyonu Sil"
          message={`“${deleteTarget.name}” organizasyonu silinecek. Bu işlem organizasyonu soft-delete olarak arşivler.`}
          confirmLabel="Sil"
          variant="danger"
          loading={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
    </PageShell>
  );
}
