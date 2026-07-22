import React from "react";
import { getFair } from "../../api/fairs";
import { FairEntitySelect } from "../FairEntitySelect";
import { FieldError, FormField } from "../ui/form";
import { operationLabels } from "../../labels/operationLabels";
import type { Fair } from "../../types/fair";

export interface FairSourcePickerProps {
  value: string[];
  onChange: (fairIds: string[]) => void;
  disabled?: boolean;
  id?: string;
  error?: string | null;
}

/**
 * Shared 1..N fair source picker for Operation Wizard.
 * Uses FairEntitySelect (no second select family).
 */
export function FairSourcePicker({
  value,
  onChange,
  disabled = false,
  id = "operation-fair-source",
  error = null,
}: FairSourcePickerProps) {
  const [pendingFairId, setPendingFairId] = React.useState("");
  const [fairNames, setFairNames] = React.useState<Record<string, string>>({});
  const [localHint, setLocalHint] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const missing = value.filter((fairId) => !fairNames[fairId]);
    if (missing.length === 0) return;

    void Promise.all(
      missing.map(async (fairId) => {
        try {
          const fair: Fair = await getFair(fairId);
          return [fairId, fair.name] as const;
        } catch {
          return [fairId, fairId] as const;
        }
      }),
    ).then((entries) => {
      if (cancelled) return;
      setFairNames((prev) => {
        const next = { ...prev };
        for (const [fairId, name] of entries) next[fairId] = name;
        return next;
      });
    });

    return () => {
      cancelled = true;
    };
  }, [value, fairNames]);

  const handleAdd = () => {
    setLocalHint(null);
    if (!pendingFairId) return;
    if (value.includes(pendingFairId)) {
      setLocalHint(operationLabels.fairSourceAlreadyAdded);
      return;
    }
    onChange([...value, pendingFairId]);
    setPendingFairId("");
  };

  const handleRemove = (fairId: string) => {
    setLocalHint(null);
    onChange(value.filter((item) => item !== fairId));
  };

  return (
    <div className="stack gap-md">
      <FormField label={operationLabels.fairSourceLabel} required>
        <div className="row gap-sm" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 240px", minWidth: 200 }}>
            <FairEntitySelect
              id={id}
              value={pendingFairId}
              onChange={setPendingFairId}
              disabled={disabled}
              placeholder={operationLabels.fairSourcePlaceholder}
            />
          </div>
          <button
            type="button"
            className="btn secondary"
            disabled={disabled || !pendingFairId}
            onClick={handleAdd}
          >
            {operationLabels.fairSourceAdd}
          </button>
        </div>
      </FormField>

      {value.length === 0 ? (
        <p className="text-muted">{operationLabels.fairSourceEmpty}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {value.map((fairId) => (
            <li
              key={fairId}
              className="row gap-sm"
              style={{
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.5rem 0",
                borderBottom: "1px solid var(--color-border, #e5e7eb)",
              }}
            >
              <span>{fairNames[fairId] ?? fairId}</span>
              <button
                type="button"
                className="btn link danger"
                disabled={disabled}
                onClick={() => handleRemove(fairId)}
              >
                {operationLabels.fairSourceRemove}
              </button>
            </li>
          ))}
        </ul>
      )}

      {localHint ? <p className="text-muted">{localHint}</p> : null}
      {error ? <FieldError>{error}</FieldError> : null}
    </div>
  );
}

