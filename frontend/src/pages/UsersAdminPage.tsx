import React from "react";
import { ApiError } from "../api/client";
import {
  createOrganizationUser,
  inviteOrganizationUser,
  listOrganizations,
  type Organization,
} from "../api/coreIdentity";
import { Banner } from "../components/ui/Banner";
import { EmptyState } from "../components/ui/EmptyState";
import { FormModal } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";

interface SubmissionResult {
  title: string;
  detail: string;
}

type CreateMode = "temporary-password" | "invite";

export function UsersAdminPage() {
  const [organizations, setOrganizations] = React.useState<Organization[]>([]);
  const [organizationsLoading, setOrganizationsLoading] = React.useState(true);
  const [mode, setMode] = React.useState<CreateMode>("temporary-password");
  const [organizationId, setOrganizationId] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [temporaryPassword, setTemporaryPassword] = React.useState("");
  const [roleSlug, setRoleSlug] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [modalOpen, setModalOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SubmissionResult | null>(null);

  const loadOrganizations = React.useCallback(async () => {
    setOrganizationsLoading(true);
    setError(null);
    try {
      const items = await listOrganizations();
      const activeOrganizations = items.filter((item) => item.status === "active");
      setOrganizations(activeOrganizations);
      setOrganizationId((current) => {
        if (current && activeOrganizations.some((item) => item.id === current)) return current;
        return activeOrganizations.length === 1 ? activeOrganizations[0].id : "";
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Organizasyonlar yüklenemedi.");
    } finally {
      setOrganizationsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadOrganizations();
  }, [loadOrganizations]);

  const resetFields = () => {
    setEmail("");
    setTemporaryPassword("");
    setRoleSlug("");
    setMode("temporary-password");
    setFormError(null);
    setOrganizationId(organizations.length === 1 ? organizations[0].id : "");
  };

  const openCreate = () => {
    resetFields();
    setResult(null);
    setModalOpen(true);
  };

  const closeCreate = () => {
    if (saving) return;
    setModalOpen(false);
    setFormError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setResult(null);

    if (!organizationId) {
      setFormError("Organizasyon seçimi zorunludur.");
      return;
    }
    if (!email.trim()) {
      setFormError("E-posta adresi zorunludur.");
      return;
    }
    if (mode === "temporary-password" && temporaryPassword.length < 8) {
      setFormError("Geçici şifre en az 8 karakter olmalıdır.");
      return;
    }

    setSaving(true);
    try {
      if (mode === "invite") {
        const response = await inviteOrganizationUser(organizationId, email.trim());
        setResult({
          title: "Davet oluşturuldu",
          detail: `Davet ${new Date(response.expires_at).toLocaleString("tr-TR")} tarihine kadar geçerli.`,
        });
      } else {
        const response = await createOrganizationUser(organizationId, {
          email: email.trim(),
          temporary_password: temporaryPassword,
          ...(roleSlug.trim() ? { role_slug: roleSlug.trim() } : {}),
        });
        setResult({
          title: "Kullanıcı oluşturuldu",
          detail: `${response.email} ilk girişinde şifresini değiştirmek zorunda.`,
        });
      }
      setModalOpen(false);
      resetFields();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Kullanıcı işlemi tamamlanamadı.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell className="users-admin-page">
      <PageHeader
        title="Kullanıcılar"
        subtitle="Organizasyon kullanıcılarını davet veya geçici şifre ile oluşturun."
        actions={[
          {
            id: "new-user",
            label: "+ Yeni Kullanıcı",
            variant: "primary",
            onClick: openCreate,
            disabled: organizationsLoading || Boolean(error),
          },
        ]}
      />

      {error ? <Banner variant="error">{error}</Banner> : null}
      {result ? (
        <Banner variant="success">
          <strong>{result.title}.</strong> {result.detail}
        </Banner>
      ) : null}

      {!error && !organizationsLoading && organizations.length === 0 ? (
        <EmptyState
          title="Önce bir organizasyon oluşturun"
          description="Kullanıcı ekleyebilmek için aktif bir organizasyon bulunmalıdır."
        />
      ) : null}

      {!error && organizationsLoading ? (
        <div className="card table-loading-state">Organizasyonlar yükleniyor…</div>
      ) : null}

      {!error && !organizationsLoading && organizations.length > 0 ? (
        <div className="card admin-summary-card">
          <div className="admin-summary-card__content">
            <strong>Kullanıcı oluşturma hazır</strong>
            <span className="muted">
              {organizations.length} aktif organizasyon kullanılabilir. Yeni kullanıcı eklemek için üstteki butonu kullanın.
            </span>
          </div>
        </div>
      ) : null}

      {modalOpen ? (
        <FormModal title="Yeni Kullanıcı" onClose={closeCreate} formWidth="standard">
          <form onSubmit={handleSubmit} className="crm-form-stack">
            {formError ? <Banner variant="error">{formError}</Banner> : null}

            <div className="form-field">
              <span className="form-label">Oluşturma Yöntemi</span>
              <div className="segmented-control" role="group" aria-label="Kullanıcı oluşturma yöntemi">
                <button
                  type="button"
                  className={`btn ${mode === "temporary-password" ? "primary" : "secondary"}`}
                  onClick={() => {
                    setMode("temporary-password");
                    setFormError(null);
                  }}
                  disabled={saving}
                >
                  Geçici Şifre
                </button>
                <button
                  type="button"
                  className={`btn ${mode === "invite" ? "primary" : "secondary"}`}
                  onClick={() => {
                    setMode("invite");
                    setFormError(null);
                  }}
                  disabled={saving}
                >
                  Davet
                </button>
              </div>
            </div>

            <label className="form-field">
              <span className="form-label">Organizasyon *</span>
              <select
                className="input"
                value={organizationId}
                onChange={(event) => setOrganizationId(event.target.value)}
                disabled={saving}
                required
              >
                <option value="">Organizasyon seçin</option>
                {organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span className="form-label">E-posta *</span>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="kullanici@firma.com"
                disabled={saving}
                required
                autoFocus
              />
            </label>

            {mode === "temporary-password" ? (
              <>
                <label className="form-field">
                  <span className="form-label">Geçici Şifre *</span>
                  <input
                    className="input"
                    type="password"
                    value={temporaryPassword}
                    onChange={(event) => setTemporaryPassword(event.target.value)}
                    minLength={8}
                    disabled={saving}
                    required
                    autoComplete="new-password"
                  />
                  <span className="form-hint">Kullanıcı ilk girişte bu şifreyi zorunlu olarak değiştirecek.</span>
                </label>
                <label className="form-field">
                  <span className="form-label">Rol</span>
                  <input
                    className="input"
                    value={roleSlug}
                    onChange={(event) => setRoleSlug(event.target.value)}
                    placeholder="Boş bırakılırsa varsayılan üye rolü"
                    disabled={saving}
                  />
                </label>
              </>
            ) : (
              <div className="form-hint-card">
                Davet seçilen organizasyon için oluşturulur. Kullanıcı daveti kabul ederken kendi şifresini belirler.
              </div>
            )}

            <div className="form-actions">
              <button type="button" className="btn secondary" onClick={closeCreate} disabled={saving}>
                Vazgeç
              </button>
              <button type="submit" className="btn primary" disabled={saving}>
                {saving ? "İşleniyor…" : mode === "invite" ? "Davet Oluştur" : "Kullanıcı Oluştur"}
              </button>
            </div>
          </form>
        </FormModal>
      ) : null}
    </PageShell>
  );
}
