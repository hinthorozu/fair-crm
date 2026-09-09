import React from "react";
import { adminLabels } from "../../labels/adminLabels";
import type { EmailAccount } from "../../types/smtp";
import {
  formatEmailAccountOptionLabel,
  resolveDefaultEmailAccountId,
} from "../../utils/emailAccountSelection";
import { FormField, SelectInput } from "../ui/form";

export interface EmailAccountPickerProps {
  id: string;
  value: string;
  onChange: (accountId: string) => void;
  accounts: EmailAccount[];
  disabled?: boolean;
  required?: boolean;
  label?: string;
  fullWidth?: boolean;
}

export function EmailAccountPicker({
  id,
  value,
  onChange,
  accounts,
  disabled = false,
  required = false,
  label = adminLabels.emailAccountPickerLabel,
  fullWidth = true,
}: EmailAccountPickerProps) {
  const empty = accounts.length === 0;
  const effectiveValue = accounts.some((account) => account.id === value)
    ? value
    : resolveDefaultEmailAccountId(accounts);

  React.useEffect(() => {
    if (effectiveValue !== value) {
      onChange(effectiveValue);
    }
  }, [effectiveValue, onChange, value]);

  return (
    <FormField label={label} htmlFor={id} required={required} fullWidth={fullWidth}>
      <SelectInput
        id={id}
        value={effectiveValue}
        disabled={disabled || empty}
        required={required && !empty}
        onChange={(event) => onChange(event.target.value)}
      >
        {empty ? (
          <option value="">{adminLabels.emailAccountPickerEmpty}</option>
        ) : (
          accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {formatEmailAccountOptionLabel(account)}
            </option>
          ))
        )}
      </SelectInput>
    </FormField>
  );
}
