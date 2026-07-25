import React from "react";
import { getFair } from "../../api/fairs";
import { FairEntitySelect } from "../FairEntitySelect";
import { NavIconClose } from "../layout/NavIcons";
import { IconButton } from "../ui/IconButton";
import { FormField, FormGrid } from "../ui/form";
import { operationLabels } from "../../labels/operationLabels";

export type FairMultiSelectItem = {
  id: string;
  name: string;
};

export interface FairMultiSelectProps {
  /** DOM id for the fair search/select control. */
  id: string;
  selected: FairMultiSelectItem[];
  onChange: (next: FairMultiSelectItem[]) => void;
  disabled?: boolean;
  required?: boolean;
  selectLabel?: string;
  selectHint?: string;
  selectedLabel?: string;
  emptyLabel?: string;
  removeLabel?: string;
  alreadySelectedMessage?: string;
  /** External field error (e.g. step validation). */
  error?: string | null;
  placeholder?: string;
  /** Fired after add/remove so callers can clear preview / step errors. */
  onSelectionMutated?: () => void;
}

/**
 * Shared multi-fair picker used by Bulk Email and Enrichment automations:
 * search/select + chip list with per-row remove.
 */
export function FairMultiSelect({
  id,
  selected,
  onChange,
  disabled = false,
  required = false,
  selectLabel = operationLabels.bulkEmailFairSelectLabel,
  selectHint = operationLabels.bulkEmailFairSelectHint,
  selectedLabel = operationLabels.bulkEmailFairSelectedLabel,
  emptyLabel = operationLabels.bulkEmailFairSelectedEmpty,
  removeLabel = operationLabels.bulkEmailFairRemove,
  alreadySelectedMessage = operationLabels.bulkEmailFairAlreadySelected,
  error = null,
  placeholder,
  onSelectionMutated,
}: FairMultiSelectProps) {
  const [pickerId, setPickerId] = React.useState("");
  const [addError, setAddError] = React.useState<string | null>(null);

  const fieldError = error ?? addError;

  const handlePickerChange = (nextId: string) => {
    setPickerId(nextId);
    setAddError(null);
    if (!nextId || disabled) return;

    if (selected.some((fair) => fair.id === nextId)) {
      setAddError(alreadySelectedMessage);
      setPickerId("");
      return;
    }

    void getFair(nextId)
      .then((fair) => {
        onChange(
          selected.some((item) => item.id === fair.id)
            ? selected
            : [...selected, { id: fair.id, name: fair.name }],
        );
        setPickerId("");
        onSelectionMutated?.();
      })
      .catch(() => {
        setPickerId("");
      });
  };

  const handleRemove = (fairId: string) => {
    if (disabled) return;
    onChange(selected.filter((item) => item.id !== fairId));
    setAddError(null);
    onSelectionMutated?.();
  };

  return (
    <FormGrid>
      <FormField
        label={selectLabel}
        htmlFor={id}
        required={required}
        fullWidth
        hint={selectHint}
        error={fieldError ?? undefined}
      >
        <FairEntitySelect
          id={id}
          value={pickerId}
          onChange={handlePickerChange}
          disabled={disabled}
          allowClear
          placeholder={placeholder}
        />
      </FormField>

      <FormField label={selectedLabel} htmlFor={`${id}-selected`} fullWidth>
        {selected.length === 0 ? (
          <p className="field-hint">{emptyLabel}</p>
        ) : (
          <ul className="selected-entity-list" id={`${id}-selected`}>
            {selected.map((fair) => (
              <li key={fair.id} className="selected-entity-item">
                <span>{fair.name}</span>
                <IconButton
                  label={removeLabel}
                  icon={<NavIconClose />}
                  disabled={disabled}
                  onClick={() => handleRemove(fair.id)}
                />
              </li>
            ))}
          </ul>
        )}
      </FormField>
    </FormGrid>
  );
}
