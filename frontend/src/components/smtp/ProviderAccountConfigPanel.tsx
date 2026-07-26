import React from "react";
import { listEmailAccountProviders, ApiError } from "../../api/emailAccounts";
import { adminLabels } from "../../labels/adminLabels";
import type {
  EmailAccountProviderDefinition,
  ErrorPolicyCategory,
  ProviderFieldDefinition,
} from "../../types/smtp";
import {
  ERROR_POLICY_ACTIONS_BY_CATEGORY,
  type ErrorPolicyGroupFormValues,
} from "../../utils/emailAccountForm";
import { Banner } from "../ui/Banner";
import {
  FormField,
  FormGrid,
  FormSection,
  PasswordInput,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../ui/form";

const CATEGORY_LABELS: Record<ErrorPolicyCategory, string> = {
  ACCOUNT_ERROR: adminLabels.smtpErrorPolicyCategoryAccount,
  DELIVERY_ERROR: adminLabels.smtpErrorPolicyCategoryDelivery,
  MESSAGE_ERROR: adminLabels.smtpErrorPolicyCategoryMessage,
};

const ACTION_LABELS: Record<string, string> = {
  fail: adminLabels.smtpErrorPolicyActionFail,
  deactivate_and_fail: adminLabels.smtpErrorPolicyActionDeactivateAndFail,
  record_and_fail: adminLabels.smtpErrorPolicyActionRecordAndFail,
  auto_retry: adminLabels.smtpErrorPolicyActionAutoRetry,
  skip: adminLabels.smtpErrorPolicyActionSkip,
};

export interface ProviderAccountConfigPanelProps {
  mode: "create" | "edit";
  providerKey: string;
  providerConfig: Record<string, string>;
  errorPolicyGroups: ErrorPolicyGroupFormValues[];
  secretsSet?: Record<string, boolean>;
  providerKeyLocked?: boolean;
  onProviderKeyChange: (providerKey: string, definition: EmailAccountProviderDefinition | null) => void;
  onProviderConfigChange: (key: string, value: string) => void;
  onErrorPolicyGroupChange: (
    category: ErrorPolicyCategory,
    patch: Partial<Pick<ErrorPolicyGroupFormValues, "identifiersText" | "action">>,
  ) => void;
  onProvidersLoaded?: (providers: EmailAccountProviderDefinition[]) => void;
}

function renderProviderField(
  field: ProviderFieldDefinition,
  value: string,
  mode: "create" | "edit",
  secretsSet: Record<string, boolean> | undefined,
  onChange: (value: string) => void,
) {
  const id = `provider-field-${field.key}`;
  const isSecret = field.secret || field.type === "password";
  const secretConfigured = Boolean(secretsSet?.[field.key]);
  const hint =
    isSecret && mode === "edit" && secretConfigured
      ? adminLabels.smtpProviderSecretConfiguredHint
      : field.help_text || undefined;

  if (isSecret) {
    return (
      <FormField
        key={field.key}
        label={field.label}
        htmlFor={id}
        required={field.required && !(mode === "edit" && secretConfigured)}
        hint={hint}
        fullWidth
      >
        <PasswordInput
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="new-password"
          placeholder={
            mode === "edit" && secretConfigured
              ? adminLabels.smtpProviderSecretKeepPlaceholder
              : field.placeholder || undefined
          }
        />
      </FormField>
    );
  }

  return (
    <FormField
      key={field.key}
      label={field.label}
      htmlFor={id}
      required={field.required}
      hint={field.help_text || undefined}
      fullWidth
    >
      <TextInput
        id={id}
        type={field.type === "email" ? "email" : "text"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={field.placeholder || undefined}
        required={field.required}
      />
    </FormField>
  );
}

/**
 * Dynamic provider account config: loads provider schemas from API and renders
 * fields + error-policy groups without adapter-specific hardcoding.
 */
export function ProviderAccountConfigPanel({
  mode,
  providerKey,
  providerConfig,
  errorPolicyGroups,
  secretsSet,
  providerKeyLocked = false,
  onProviderKeyChange,
  onProviderConfigChange,
  onErrorPolicyGroupChange,
  onProvidersLoaded,
}: ProviderAccountConfigPanelProps) {
  const [providers, setProviders] = React.useState<EmailAccountProviderDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void listEmailAccountProviders()
      .then((response) => {
        if (cancelled) return;
        setProviders(response.items);
        onProvidersLoaded?.(response.items);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof ApiError ? err.message : adminLabels.smtpProviderLoadError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onProvidersLoaded]);

  const selectedDefinition = React.useMemo(
    () => providers.find((item) => item.provider_key === providerKey) ?? null,
    [providers, providerKey],
  );

  const handleProviderSelect = (nextKey: string) => {
    const definition = providers.find((item) => item.provider_key === nextKey) ?? null;
    onProviderKeyChange(nextKey, definition);
  };

  return (
    <>
      <FormSection title={adminLabels.smtpSectionProvider}>
        {loadError ? <Banner variant="error">{loadError}</Banner> : null}
        <FormGrid>
          <FormField
            label={adminLabels.smtpProviderFieldProvider}
            htmlFor="email-account-provider-key"
            required
            fullWidth
          >
            <SelectInput
              id="email-account-provider-key"
              value={providerKey}
              onChange={(event) => handleProviderSelect(event.target.value)}
              disabled={providerKeyLocked || loading || Boolean(loadError)}
              required
            >
              <option value="">{adminLabels.smtpProviderSelectPlaceholder}</option>
              {providers.map((provider) => (
                <option key={provider.provider_key} value={provider.provider_key}>
                  {provider.display_name}
                </option>
              ))}
            </SelectInput>
          </FormField>

          {selectedDefinition
            ? selectedDefinition.fields.map((field) =>
                renderProviderField(
                  field,
                  providerConfig[field.key] ?? "",
                  mode,
                  secretsSet,
                  (value) => onProviderConfigChange(field.key, value),
                ),
              )
            : null}
        </FormGrid>
      </FormSection>

      {selectedDefinition ? (
        <FormSection title={adminLabels.smtpSectionErrorPolicy}>
          {errorPolicyGroups.map((group) => {
            const actions = ERROR_POLICY_ACTIONS_BY_CATEGORY[group.category];
            const identifiersId = `error-policy-identifiers-${group.category}`;
            const actionId = `error-policy-action-${group.category}`;
            return (
              <div key={group.category} className="email-account-error-policy-group">
                <h4 className="email-account-error-policy-group__title">
                  {CATEGORY_LABELS[group.category]}
                </h4>
                <FormGrid>
                  <FormField
                    label={adminLabels.smtpErrorPolicyIdentifiersLabel}
                    htmlFor={identifiersId}
                    hint={adminLabels.smtpErrorPolicyIdentifiersHint}
                    fullWidth
                  >
                    <TextareaInput
                      id={identifiersId}
                      rows={2}
                      value={group.identifiersText}
                      onChange={(event) =>
                        onErrorPolicyGroupChange(group.category, {
                          identifiersText: event.target.value,
                        })
                      }
                      placeholder="401, 403, 429"
                    />
                  </FormField>
                  <FormField
                    label={adminLabels.smtpErrorPolicyActionLabel}
                    htmlFor={actionId}
                    required
                  >
                    <SelectInput
                      id={actionId}
                      value={group.action}
                      onChange={(event) =>
                        onErrorPolicyGroupChange(group.category, { action: event.target.value })
                      }
                    >
                      {actions.map((action) => (
                        <option key={action} value={action}>
                          {ACTION_LABELS[action] ?? action}
                        </option>
                      ))}
                    </SelectInput>
                  </FormField>
                </FormGrid>
              </div>
            );
          })}
        </FormSection>
      ) : null}
    </>
  );
}
