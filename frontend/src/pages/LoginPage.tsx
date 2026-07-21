import React from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { labels } from "../labels";
import { authLabels } from "../labels/authLabels";
import { Banner } from "../components/ui/Banner";
import { Card } from "../components/ui/Card";
import { FormField, PasswordInput, TextInput } from "../components/ui/form";

interface LoginPageProps {
  onSuccess: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    document.title = `${labels.appTitle} — ${authLabels.pageTitle}`;
  }, []);

  const validate = (): boolean => {
    const nextErrors: { email?: string; password?: string } = {};
    if (!email.trim()) {
      nextErrors.email = authLabels.emailRequired;
    }
    if (!password) {
      nextErrors.password = authLabels.passwordRequired;
    }
    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError(authLabels.loginFailed);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page-inner">
        <div className="login-page-brand">
          <span className="login-page-brand-mark">F</span>
          <h1 className="login-page-title">{labels.appTitle}</h1>
          <p className="login-page-subtitle">{authLabels.subtitle}</p>
        </div>

        <Card className="login-card">
          <h2 className="login-card-heading">{authLabels.pageTitle}</h2>
          <form
            className="crm-form login-form"
            onSubmit={handleSubmit}
            noValidate
            aria-busy={submitting}
          >
            {formError ? <Banner variant="error">{formError}</Banner> : null}

            <FormField
              label={authLabels.email}
              htmlFor="login-email"
              required
              error={fieldErrors.email}
              fullWidth
            >
              <TextInput
                id="login-email"
                type="email"
                autoComplete="email"
                autoFocus
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

            <FormField
              label={authLabels.password}
              htmlFor="login-password"
              required
              error={fieldErrors.password}
              fullWidth
            >
              <PasswordInput
                id="login-password"
                autoComplete="current-password"
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

            <div className="login-form-actions">
              <button type="submit" className="btn primary login-submit" disabled={submitting}>
                {submitting ? authLabels.submitting : authLabels.submit}
              </button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
