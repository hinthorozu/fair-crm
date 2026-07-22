import React from "react";
import { ApiError } from "../../api/client";
import { completeTodo } from "../../api/todos";
import { todoLabels } from "../../labels/todoLabels";
import type { Todo } from "../../types/todo";
import { Button } from "../ui/Button";
import {
  FieldError,
  FormField,
  FormModal,
  TextareaInput,
} from "../ui/form";

const COMPLETE_FORM_ID = "todo-complete-form";

interface CompleteTodoModalProps {
  todo: Todo;
  onClose: () => void;
  onCompleted: (todo: Todo) => void;
}

export function CompleteTodoModal({ todo, onClose, onCompleted }: CompleteTodoModalProps) {
  const [note, setNote] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await completeTodo(todo.id, {
        note: note.trim() || null,
      });
      onCompleted(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <FormModal
      title={todoLabels.completeModalTitle}
      onClose={onClose}
      formWidth="standard"
      footer={
        <>
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
            {todoLabels.cancel}
          </Button>
          <Button type="submit" form={COMPLETE_FORM_ID} variant="primary" loading={saving}>
            {saving ? todoLabels.saving : todoLabels.completeAndRecord}
          </Button>
        </>
      }
    >
      <form id={COMPLETE_FORM_ID} onSubmit={(event) => void handleSubmit(event)}>
        <FormField
          label={todoLabels.completeNote}
          htmlFor="todo-complete-note"
          fullWidth
          hint={todoLabels.completeNoteHint}
        >
          <TextareaInput
            id="todo-complete-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={4}
            placeholder={todoLabels.completeNotePlaceholder}
            disabled={saving}
          />
        </FormField>
        {error ? <FieldError>{error}</FieldError> : null}
      </form>
    </FormModal>
  );
}
