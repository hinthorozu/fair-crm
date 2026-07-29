import React from "react";
import { createTodoStepFormItem, type TodoStepFormItem } from "../../utils/todoStepForm";
import { todoLabels } from "../../labels/todoLabels";
import { TextInput } from "../ui/form";

interface TodoStepFieldListProps {
  items: TodoStepFormItem[];
  onChange: (items: TodoStepFormItem[]) => void;
}

/** Dynamic step list — same UX pattern as CustomerCommunicationFieldList (without primary). */
export function TodoStepFieldList({ items, onChange }: TodoStepFieldListProps) {
  const fieldId = React.useId();

  const setTitle = (id: string, title: string) => {
    onChange(items.map((item) => (item.id === id ? { ...item, title } : item)));
  };

  const removeItem = (id: string) => {
    onChange(items.filter((item) => item.id !== id));
  };

  const addItem = () => {
    onChange([...items, createTodoStepFormItem("")]);
  };

  return (
    <fieldset className="communication-field-section span-2 todo-step-field-section">
      <legend className="communication-field-legend">{todoLabels.stepsSection}</legend>

      {items.length === 0 ? (
        <p className="communication-field-empty">{todoLabels.stepsEmpty}</p>
      ) : (
        <ul className="communication-field-list">
          {items.map((item, index) => (
            <li key={item.id} className="communication-field-row todo-step-field-row">
              <TextInput
                id={`${fieldId}-${index}`}
                type="text"
                className="communication-field-input"
                value={item.title}
                placeholder={todoLabels.stepPlaceholder}
                onChange={(event) => setTitle(item.id, event.target.value)}
                aria-label={`${todoLabels.stepLabel} ${index + 1}`}
              />
              <button
                type="button"
                className="btn secondary btn-sm communication-field-remove"
                onClick={() => removeItem(item.id)}
              >
                {todoLabels.stepRemove}
              </button>
            </li>
          ))}
        </ul>
      )}

      <button type="button" className="btn secondary btn-sm communication-field-add" onClick={addItem}>
        {todoLabels.stepAdd}
      </button>
    </fieldset>
  );
}
