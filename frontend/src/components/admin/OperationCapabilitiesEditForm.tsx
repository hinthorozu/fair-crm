import React from "react";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { adminLabels } from "../../labels/adminLabels";
import type {
  OperationTypeCapabilityKey,
  OperationTypeCatalogItem,
  UpdateOperationTypeCapabilitiesPayload,
} from "../../types/operation";
import { Banner } from "../ui/Banner";
import {
  CheckboxField,
  FormActions,
  FormField,
  FormSection,
  TextInput,
} from "../ui/form";

const CAPABILITY_FIELDS: Array<{
  key: OperationTypeCapabilityKey;
  label: string;
  hint: string;
}> = [
  {
    key: "supports_pause",
    label: adminLabels.operationCapabilitySupportsPause,
    hint: adminLabels.operationCapabilitySupportsPauseHint,
  },
  {
    key: "supports_resume",
    label: adminLabels.operationCapabilitySupportsResume,
    hint: adminLabels.operationCapabilitySupportsResumeHint,
  },
  {
    key: "supports_retry",
    label: adminLabels.operationCapabilitySupportsRetry,
    hint: adminLabels.operationCapabilitySupportsRetryHint,
  },
  {
    key: "supports_schedule",
    label: adminLabels.operationCapabilitySupportsSchedule,
    hint: adminLabels.operationCapabilitySupportsScheduleHint,
  },
  {
    key: "supports_items",
    label: adminLabels.operationCapabilitySupportsItems,
    hint: adminLabels.operationCapabilitySupportsItemsHint,
  },
];

function draftFromItem(item: OperationTypeCatalogItem): UpdateOperationTypeCapabilitiesPayload {
  return {
    supports_pause: item.supports_pause,
    supports_resume: item.supports_resume,
    supports_retry: item.supports_retry,
    supports_schedule: item.supports_schedule,
    supports_items: item.supports_items,
    is_active: item.is_active,
  };
}

interface OperationCapabilitiesEditFormProps {
  item: OperationTypeCatalogItem;
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (payload: UpdateOperationTypeCapabilitiesPayload) => Promise<void>;
}

export function OperationCapabilitiesEditForm({
  item,
  saving,
  error,
  onCancel,
  onSubmit,
}: OperationCapabilitiesEditFormProps) {
  const baseline = React.useMemo(() => draftFromItem(item), [item]);
  const [values, setValues] = React.useState(baseline);

  React.useEffect(() => {
    setValues(baseline);
  }, [baseline]);

  useReportFormDirty(values, baseline);
  const handleCancel = useModalFormCancel(onCancel);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await onSubmit(values);
  };

  return (
    <form
      className="operation-capabilities-edit-form crm-form crm-form--standard"
      onSubmit={(event) => void handleSubmit(event)}
    >
      {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}

      <FormSection title={adminLabels.operationCapabilitiesEditTitle}>
        <FormField
          label={adminLabels.operationCapabilitiesNameLabel}
          htmlFor="operation-capability-name"
          fullWidth
        >
          <TextInput id="operation-capability-name" value={item.name} readOnly disabled />
        </FormField>

        <CheckboxField
          id="operation-capability-is-active"
          label={adminLabels.operationCapabilitiesActiveLabel}
          hint={adminLabels.operationCapabilitiesActiveHint}
          checked={values.is_active}
          onChange={(checked) => setValues((current) => ({ ...current, is_active: checked }))}
        />

        <div className="operation-capabilities-toggles">
          {CAPABILITY_FIELDS.map((field) => (
            <CheckboxField
              key={field.key}
              id={`operation-capability-${field.key}`}
              label={field.label}
              hint={field.hint}
              checked={values[field.key]}
              onChange={(checked) =>
                setValues((current) => ({ ...current, [field.key]: checked }))
              }
            />
          ))}
        </div>
      </FormSection>

      <FormActions
        onCancel={handleCancel}
        submitLabel={adminLabels.operationCapabilitiesSave}
        cancelLabel={adminLabels.cancel}
        saving={saving}
        savingLabel={adminLabels.operationCapabilitiesSaving}
      />
    </form>
  );
}
