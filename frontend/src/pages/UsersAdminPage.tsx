import React from "react";
import { ApiError } from "../api/client";
import {
  createOrganizationUser,
  inviteOrganizationUser,
  listOrganizations,
  type Organization,
} from "../api/coreIdentity";
import { Banner } from "../components/ui/Banner";
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
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SubmissionResult | null>(null);

  React.useEffect(() => {
    let active = true;
    const load = async () => {
      setOrganizationsLoading(true);
      setError(null);
      try {
        const items = await listOrganizations();
        if (!active) return;
        const activeOrganizations = items.filter((item) => item.status === "active");
        setOrganizations(activeOrganizations);
        if (activeOrganizations.length === 1) setOrganizationId(activeOrganizations[0].id);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.message : "Organizasyonlar yüklenemedi.");
        }
      } finally {
        if (active) setOrganizationsLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  const resetFields = () => {
    setEmail("");
    setTemporaryPassword("");
    setRoleSlug("");
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setResult(null);

    if (!organizationId) {
      setError("Organizasyon seçimi zorunludur.");
      return;
    }
    if (!email.trim()) {
      setError("E-posta adresi zorunludur.");
      return;
    }
    if (mode === "temporary-password" && temporaryPassword.length < 8) {
      setError("Geçici şifre en az 8 karakter olmalıdır.");
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
      resetFields();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kullanıcı işlemi tamamlanamadı.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell className="users-admin-page">
      <PageHeader
        title="Kullanıcılar"
        subtitle="Kullanıcıyı organizasyona davet edin veya geçici şifreyle oluşturun."
      />

      {error ? <Banner variant="error">{error}</Banner> : null}
      {result ? (
        <Banner variant="success">
          <strong>{result.title}.</strong> {result.detail}
        </Banner>
      ) : null}

      <div className="card admin-user-create-card">
        <form onSubmit={handleSubmit} className="crm-form crm-form--standard crm-form-stack">
          <div className="form-field">
            <span className="form-label">Oluşturma Yöntemi</span>
            <div className="segmented-control" role="group" aria-label="Kullanıcı oluşturma yöntemi">
              <button
                type="button"
                className={`btn ${mode === "temporary-password" ? "primary" : "secondary"}`}
                onClick={() => {
                  setMode("temporary-password");
                  setResult(null);
                  setError(null);
                }}
              >
                Geçici Şifre
              </button>
              <button
                type="button"
                className={`btn ${mode === "invite" ? "primary" : "secondary"}`}
                onClick={() => {
                  setMode("invite");
                  setResult(null);
                  setError(null);
                }}
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
              disabled={organizationsLoading || saving}
              required
            >
              <option value="">
                {organizationsLoading ? "Organizasyonlar yükleniyor…" : "Organizasyon seçin"}
              </option>
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
            {!organizationsLoading && organizations.length === 0 ? (
              <span className="form-hint">Önce Organizasyonlar ekranından bir organizasyon oluşturun.</span>
            ) : null}
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
            <p className="text-muted">
              Davet, seçilen organizasyon için oluşturulur. Kullanıcı daveti kabul ederken kendi şifresini belirler.
            </p>
          )}

          <div className="form-actions">
            <button
              type="submit"
              className="btn primary"
              disabled={saving || organizationsLoading || organizations.length === 0}
            >
              {saving
                ? "İşleniyor…"
                : mode === "invite"
                  ? "Davet Oluştur"
                  : "Kullanıcı Oluştur"}
            </button>
          </div>
        </form>
      </div>
    </PageShell>
  );
}
