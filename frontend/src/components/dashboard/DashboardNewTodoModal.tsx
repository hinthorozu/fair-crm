import React from "react";
import { createTodo } from "../../api/todos";
import { replaceTodoSteps } from "../../api/todoSteps";
import {
  TODO_FORM_ID,
  TodoForm,
  formValuesToCreatePayload,
  type TodoFormValues,
} from "../todos/TodoForm";
import { Button } from "../ui/Button";
import { FormModal } from "../ui/form";
import { useModalFormCancel } from "../../hooks/useModalForm";
import { todoLabels } from "../../labels/todoLabels";
import { getGrantedCorePermissions } from "../../permissions/corePermissions";
import { TODO_PERMISSION_CREATE } from "../../permissions/todoPermissions";
import { formItemsToReplacePayload } from "../../utils/todoStepForm";

function CancelButton({ onClose, disabled }: { onClose: () => void; disabled: boolean }) {
  const requestClose = useModalFormCancel(onClose);
  return (
    <Button type="button" variant="secondary" onClick={requestClose} disabled={disabled}>
      {todoLabels.cancel}
    </Button>
  );
}

export function DashboardNewTodoModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [saving, setSaving] = React.useState(false);
  const canCreateTodo = getGrantedCorePermissions().has(TODO_PERMISSION_CREATE);

  const handleCreate = async (values: TodoFormValues) => {
    if (!canCreateTodo) return;
    const created = await createTodo(formValuesToCreatePayload(values));
    const stepPayload = formItemsToReplacePayload(values.steps);
    if (stepPayload.length > 0) {
      await replaceTodoSteps(created.id, { steps: stepPayload });
    }
    onCreated();
  };

  return (
    <FormModal
      title={todoLabels.newTodo}
      onClose={onClose}
      size="lg"
      formWidth="standard"
      footer={
        <>
          <CancelButton onClose={onClose} disabled={saving} />
          {canCreateTodo ? (
            <Button
              type="submit"
              form={TODO_FORM_ID}
              variant="primary"
              loading={saving}
            >
              {saving ? todoLabels.saving : todoLabels.save}
            </Button>
          ) : null}
        </>
      }
    >
      <TodoForm onSubmit={handleCreate} onSavingChange={setSaving} />
    </FormModal>
  );
}
