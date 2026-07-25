import React from "react";
import { adminLabels } from "../../labels/adminLabels";
import type { EmailAccount } from "../../types/smtp";
import { formatEmailAccountOptionLabel } from "../../utils/emailAccountSelection";
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

  return (
    <FormField label={label} htmlFor={id} required={required} fullWidth={fullWidth}>
      <SelectInput
        id={id}
        value={empty ? "" : value}
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
