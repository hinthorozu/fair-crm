import React from "react";
import { ApiError } from "../../api/client";
import { updateTodoStep } from "../../api/todoSteps";
import { todoLabels } from "../../labels/todoLabels";
import type { TodoStep } from "../../types/todoStep";
import { CheckboxField } from "../ui/form";

interface TodoChecklistProps {
  todoId: string;
  steps: TodoStep[];
  onStepsChange: (steps: TodoStep[]) => void;
  canToggle: boolean;
}

export function TodoChecklist({ todoId, steps, onStepsChange, canToggle }: TodoChecklistProps) {
  const [pendingId, setPendingId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const stepsRef = React.useRef(steps);
  stepsRef.current = steps;

  if (steps.length === 0) {
    return null;
  }

  const handleToggle = async (step: TodoStep, checked: boolean) => {
    if (!canToggle || pendingId) return;
    setPendingId(step.id);
    setError(null);
    const previous = stepsRef.current;
    onStepsChange(
      previous.map((item) => (item.id === step.id ? { ...item, is_completed: checked } : item)),
    );
    try {
      const updated = await updateTodoStep(todoId, step.id, { is_completed: checked });
      onStepsChange(
        stepsRef.current.map((item) => (item.id === step.id ? updated : item)),
      );
    } catch (err) {
      onStepsChange(previous);
      setError(err instanceof ApiError ? err.message : todoLabels.stepsLoadError);
    } finally {
      setPendingId(null);
    }
  };

  return (
    <section className="todo-checklist-section">
      <h3 className="todo-checklist-title">{todoLabels.stepsSection}</h3>
      {error ? <p className="text-danger">{error}</p> : null}
      <ul className="todo-checklist">
        {steps.map((step) => (
          <li key={step.id} className="todo-checklist-item">
            <CheckboxField
              id={`todo-step-${step.id}`}
              label={step.title}
              hideLabel
              checked={step.is_completed}
              disabled={!canToggle || pendingId === step.id}
              onChange={(checked) => void handleToggle(step, checked)}
              className="todo-checklist-checkbox"
              inputClassName="todo-checklist-input"
            />
            <span
              className={
                step.is_completed ? "todo-checklist-text is-completed" : "todo-checklist-text"
              }
            >
              {step.title}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
