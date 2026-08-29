import React from "react";
import { ApiError } from "../api/client";
import {
  completeAccountActivation,
  requestPasswordReset,
  resetPassword,
  signupAccount,
} from "../api/auth";
import { Banner } from "../components/ui/Banner";
import { Card } from "../components/ui/Card";
import { PageShell } from "../components/ui/PageShell";
import { FormField, PasswordInput, TextInput } from "../components/ui/form";
import { labels } from "../labels";
import { authLabels } from "../labels/authLabels";

export type PublicAuthPath = "/signup" | "/activate" | "/forgot-password" | "/reset-password";

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) return pathname.slice(0, -1);
  return pathname;
}

export function isPublicAuthPath(pathname: string): pathname is PublicAuthPath {
  const normalized = normalizePath(pathname);
  return (
    normalized === "/signup" ||
    normalized === "/activate" ||
    normalized === "/forgot-password" ||
    normalized === "/reset-password"
  );
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : authLabels.requestFailed;
}

function PublicAuthFrame({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  React.useEffect(() => {
    document.title = `${labels.appTitle} — ${title}`;
  }, [title]);

  return (
    <PageShell className="login-page" fullWidth>
      <div className="login-page-inner">
        <div className="login-page-brand">
          <span className="login-page-brand-mark">F</span>
          <h1 className="login-page-title">{labels.appTitle}</h1>
          <p className="login-page-subtitle">{subtitle}</p>
        </div>
        <Card className="login-card">
          <h2 className="login-card-heading">{title}</h2>
          {children}
        </Card>
      </div>
    </PageShell>
  );
}

function LoginLink() {
  return (
    <div className="login-form-actions">
      <a className="btn secondary" href="/login">
        {authLabels.backToLogin}
      </a>
    </div>
  );
}

export function SignupPage() {
  const [organizationName, setOrganizationName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<{
    organizationName?: string;
    email?: string;
  }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const nextErrors: typeof fieldErrors = {};
    if (!organizationName.trim()) nextErrors.organizationName = authLabels.organizationNameRequired;
    if (!email.trim()) nextErrors.email = authLabels.emailRequired;
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await signupAccount({ organization_name: organizationName.trim(), email: email.trim() });
      setSuccess(true);
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PublicAuthFrame title={authLabels.signupTitle} subtitle={authLabels.signupSubtitle}>
      {success ? (
        <>
          <Banner variant="success">{authLabels.signupSuccess}</Banner>
          <LoginLink />
        </>
      ) : (
        <form className="crm-form crm-form--narrow login-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
          {formError ? <Banner variant="error">{formError}</Banner> : null}
          <FormField
            label={authLabels.organizationName}
            htmlFor="signup-organization-name"
            required
            error={fieldErrors.organizationName}
            fullWidth
          >
            <TextInput
              id="signup-organization-name"
              autoComplete="organization"
              autoFocus
              value={organizationName}
              disabled={submitting}
              aria-invalid={fieldErrors.organizationName ? true : undefined}
              onChange={(event) => {
                setOrganizationName(event.target.value);
                setFieldErrors((current) => ({ ...current, organizationName: undefined }));
                setFormError(null);
              }}
            />
          </FormField>
          <FormField label={authLabels.email} htmlFor="signup-email" required error={fieldErrors.email} fullWidth>
            <TextInput
              id="signup-email"
              type="email"
              autoComplete="email"
              value={email}
              disabled={submitting}
              aria-invalid={fieldErrors.email ? true : undefined}
              onChange={(event) => {
                setEmail(event.target.value);
                setFieldErrors((current) => ({ ...current, email: undefined }));
                setFormError(null);
              }}
            />
          </FormField>
          <div className="login-form-actions">
            <button type="submit" className="btn primary login-submit" disabled={submitting}>
              {submitting ? authLabels.signupSubmitting : authLabels.signupSubmit}
            </button>
            <a className="btn secondary" href="/login">{authLabels.backToLogin}</a>
          </div>
        </form>
      )}
    </PublicAuthFrame>
  );
}

function PasswordSetForm({
  token,
  mode,
}: {
  token: string;
  mode: "activation" | "reset";
}) {
  const activation = mode === "activation";
  const title = activation ? authLabels.activationTitle : authLabels.resetPasswordTitle;
  const subtitle = activation ? authLabels.activationSubtitle : authLabels.resetPasswordSubtitle;
  const submitLabel = activation ? authLabels.activationSubmit : authLabels.resetPasswordSubmit;
  const submittingLabel = activation ? authLabels.activationSubmitting : authLabels.resetPasswordSubmitting;
  const successLabel = activation ? authLabels.activationSuccess : authLabels.resetPasswordSuccess;
  const [password, setPassword] = React.useState("");
  const [confirmation, setConfirmation] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<{ password?: string; confirmation?: string }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const nextErrors: typeof fieldErrors = {};
    if (!password) nextErrors.password = authLabels.newPasswordRequired;
    if (!confirmation) nextErrors.confirmation = authLabels.confirmPasswordRequired;
    if (password && confirmation && password !== confirmation) {
      nextErrors.confirmation = authLabels.passwordMismatch;
    }
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    if (!token) {
      setFormError(authLabels.tokenMissing);
      return;
    }

    setSubmitting(true);
    try {
      if (activation) {
        await completeAccountActivation({ token, password });
      } else {
        await resetPassword({ token, password });
      }
      setPassword("");
      setConfirmation("");
      setSuccess(true);
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PublicAuthFrame title={title} subtitle={subtitle}>
      {!token ? (
        <>
          <Banner variant="error">{authLabels.tokenMissing}</Banner>
          <LoginLink />
        </>
      ) : success ? (
        <>
          <Banner variant="success">{successLabel}</Banner>
          <LoginLink />
        </>
      ) : (
        <form className="crm-form crm-form--narrow login-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
          {formError ? <Banner variant="error">{formError}</Banner> : null}
          <FormField
            label={authLabels.newPassword}
            htmlFor={`${mode}-password`}
            required
            error={fieldErrors.password}
            hint={authLabels.passwordPolicyHint}
            fullWidth
          >
            <PasswordInput
              id={`${mode}-password`}
              autoComplete="new-password"
              autoFocus
              maxLength={255}
              value={password}
              disabled={submitting}
              aria-invalid={fieldErrors.password ? true : undefined}
              onChange={(event) => {
                setPassword(event.target.value);
                setFieldErrors((current) => ({ ...current, password: undefined }));
                setFormError(null);
              }}
            />
          </FormField>
          <FormField
            label={authLabels.confirmPassword}
            htmlFor={`${mode}-password-confirmation`}
            required
            error={fieldErrors.confirmation}
            fullWidth
          >
            <PasswordInput
              id={`${mode}-password-confirmation`}
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
            <button type="submit" className="btn primary login-submit" disabled={submitting}>
              {submitting ? submittingLabel : submitLabel}
            </button>
            <a className="btn secondary" href="/login">{authLabels.backToLogin}</a>
          </div>
        </form>
      )}
    </PublicAuthFrame>
  );
}

export function ActivationPage({ token }: { token: string }) {
  return <PasswordSetForm token={token} mode="activation" />;
}

export function ForgotPasswordPage() {
  const [email, setEmail] = React.useState("");
  const [fieldError, setFieldError] = React.useState<string | undefined>();
  const [formError, setFormError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    if (!email.trim()) {
      setFieldError(authLabels.emailRequired);
      return;
    }

    setSubmitting(true);
    try {
      await requestPasswordReset({ email: email.trim() });
      setSuccess(true);
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PublicAuthFrame title={authLabels.forgotPasswordTitle} subtitle={authLabels.forgotPasswordSubtitle}>
      {success ? (
        <>
          <Banner variant="success">{authLabels.forgotPasswordSuccess}</Banner>
          <LoginLink />
        </>
      ) : (
        <form className="crm-form crm-form--narrow login-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
          {formError ? <Banner variant="error">{formError}</Banner> : null}
          <FormField label={authLabels.email} htmlFor="forgot-email" required error={fieldError} fullWidth>
            <TextInput
              id="forgot-email"
              type="email"
              autoComplete="email"
              autoFocus
              value={email}
              disabled={submitting}
              aria-invalid={fieldError ? true : undefined}
              onChange={(event) => {
                setEmail(event.target.value);
                setFieldError(undefined);
                setFormError(null);
              }}
            />
          </FormField>
          <div className="login-form-actions">
            <button type="submit" className="btn primary login-submit" disabled={submitting}>
              {submitting ? authLabels.forgotPasswordSubmitting : authLabels.forgotPasswordSubmit}
            </button>
            <a className="btn secondary" href="/login">{authLabels.backToLogin}</a>
          </div>
        </form>
      )}
    </PublicAuthFrame>
  );
}

export function ResetPasswordPage({ token }: { token: string }) {
  return <PasswordSetForm token={token} mode="reset" />;
}

export function PublicAuthRouter() {
  const pathname = normalizePath(window.location.pathname);
  const [token] = React.useState(() => new URLSearchParams(window.location.search).get("token")?.trim() ?? "");

  React.useEffect(() => {
    if ((pathname === "/activate" || pathname === "/reset-password") && token && window.location.search) {
      window.history.replaceState(null, "", pathname);
    }
  }, [pathname, token]);

  if (pathname === "/signup") return <SignupPage />;
  if (pathname === "/activate") return <ActivationPage token={token} />;
  if (pathname === "/forgot-password") return <ForgotPasswordPage />;
  return <ResetPasswordPage token={token} />;
}
