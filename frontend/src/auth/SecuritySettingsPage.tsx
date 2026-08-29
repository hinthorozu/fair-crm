import React from "react";
import { changePassword } from "../api/auth";
import { ApiError } from "../api/client";
import { Banner } from "../components/ui/Banner";
import { Card } from "../components/ui/Card";
import { FormField, PasswordInput } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { labels } from "../labels";
import { authLabels } from "../labels/authLabels";

export function isSecuritySettingsPath(pathname: string): boolean {
  const normalized = pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  return normalized === "/settings/security";
}

interface SecuritySettingsPageProps {
  accessToken: string;
  onPasswordChanged: () => void;
}

export function SecuritySettingsPage({ accessToken, onPasswordChanged }: SecuritySettingsPageProps) {
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmation, setConfirmation] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<{
    currentPassword?: string;
    newPassword?: string;
    confirmation?: string;
  }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    document.title = `${labels.appTitle} — ${authLabels.securityTitle}`;
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);

    const nextErrors: typeof fieldErrors = {};
    if (!currentPassword) nextErrors.currentPassword = authLabels.currentPasswordRequired;
    if (!newPassword) nextErrors.newPassword = authLabels.newPasswordRequired;
    if (!confirmation) nextErrors.confirmation = authLabels.confirmPasswordRequired;
    if (newPassword && confirmation && newPassword !== confirmation) {
      nextErrors.confirmation = authLabels.passwordMismatch;
    }
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await changePassword(
        {
          current_password: currentPassword,
          new_password: newPassword,
        },
        accessToken,
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      onPasswordChanged();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : authLabels.requestFailed);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageShell className="security-settings-page">
      <PageHeader title={authLabels.securityTitle} />
      <Card>
        <p className="text-muted">{authLabels.securitySubtitle}</p>
        <form
          className="crm-form crm-form--narrow"
          onSubmit={handleSubmit}
          noValidate
          aria-busy={submitting}
        >
          {formError ? <Banner variant="error">{formError}</Banner> : null}

          <FormField
            label={authLabels.currentPassword}
            htmlFor="security-current-password"
            required
            error={fieldErrors.currentPassword}
            fullWidth
          >
            <PasswordInput
              id="security-current-password"
              autoComplete="current-password"
              autoFocus
              maxLength={255}
              value={currentPassword}
              disabled={submitting}
              aria-invalid={fieldErrors.currentPassword ? true : undefined}
              onChange={(event) => {
                setCurrentPassword(event.target.value);
                setFieldErrors((current) => ({ ...current, currentPassword: undefined }));
                setFormError(null);
              }}
            />
          </FormField>

          <FormField
            label={authLabels.newPassword}
            htmlFor="security-new-password"
            required
            error={fieldErrors.newPassword}
            hint={authLabels.passwordPolicyHint}
            fullWidth
          >
            <PasswordInput
              id="security-new-password"
              autoComplete="new-password"
              maxLength={255}
              value={newPassword}
              disabled={submitting}
              aria-invalid={fieldErrors.newPassword ? true : undefined}
              onChange={(event) => {
                setNewPassword(event.target.value);
                setFieldErrors((current) => ({ ...current, newPassword: undefined }));
                setFormError(null);
              }}
            />
          </FormField>

          <FormField
            label={authLabels.confirmPassword}
            htmlFor="security-confirm-password"
            required
            error={fieldErrors.confirmation}
            fullWidth
          >
            <PasswordInput
              id="security-confirm-password"
              autoComplete="new-password"
              maxLength={255}
              value={confirmation}
              disabled={submitting}
              aria-invalid={fieldErrors.confirmation ? true : undefined}
              onChange={(event) => {
                setConfirmation(event.target.value);
                setFieldErrors((current) => ({ ...current, confirmation: undefined }));
                setFormError(null);
              }}
            />
          </FormField>

          <div className="login-form-actions">
            <button type="submit" className="btn primary" disabled={submitting}>
              {submitting ? authLabels.changePasswordSubmitting : authLabels.changePasswordSubmit}
            </button>
            <a className="btn secondary" href="/dashboard">
              {authLabels.backToApp}
            </a>
          </div>
        </form>
      </Card>
    </PageShell>
  );
}
