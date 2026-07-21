import React from "react";
import type { CommunicationFormItem } from "../utils/customerCommunicationForm";
import { createCommunicationItem, ensureSinglePrimary } from "../utils/customerCommunicationForm";
import { labels } from "../labels";
import { TextInput, RadioField } from "./ui/form";

interface CustomerCommunicationFieldListProps {
  sectionLabel: string;
  items: CommunicationFormItem[];
  onChange: (items: CommunicationFormItem[]) => void;
  inputType?: "text" | "email" | "tel";
  placeholder?: string;
}

export function CustomerCommunicationFieldList({
  sectionLabel,
  items,
  onChange,
  inputType = "text",
  placeholder,
}: CustomerCommunicationFieldListProps) {
  const fieldId = React.useId();

  const updateItems = (next: CommunicationFormItem[]) => {
    onChange(ensureSinglePrimary(next));
  };

  const setValue = (id: string, value: string) => {
    updateItems(items.map((item) => (item.id === id ? { ...item, value } : item)));
  };

  const setPrimary = (id: string) => {
    updateItems(
      items.map((item) => ({
        ...item,
        is_primary: item.id === id,
      })),
    );
  };

  const removeItem = (id: string) => {
    updateItems(items.filter((item) => item.id !== id));
  };

  const addItem = () => {
    const next = [...items, createCommunicationItem("", items.length === 0)];
    updateItems(next);
  };

  return (
    <fieldset className="communication-field-section span-2">
      <legend className="communication-field-legend">{sectionLabel}</legend>

      {items.length === 0 ? (
        <p className="communication-field-empty">{labels.communicationEmpty}</p>
      ) : (
        <ul className="communication-field-list">
          {items.map((item, index) => (
            <li key={item.id} className="communication-field-row">
              <RadioField
                id={`${fieldId}-primary-${item.id}`}
                name={`${fieldId}-primary`}
                label={labels.primary}
                value={item.id}
                checked={item.is_primary}
                onChange={() => setPrimary(item.id)}
                ariaLabel={`${labels.markPrimary} ${sectionLabel}`}
                className="communication-field-primary"
              />
              <TextInput
                id={`${fieldId}-${index}`}
                type={inputType}
                className="communication-field-input"
                value={item.value}
                placeholder={placeholder}
                onChange={(event) => setValue(item.id, event.target.value)}
              />
              <button
                type="button"
                className="btn secondary btn-sm communication-field-remove"
                onClick={() => removeItem(item.id)}
              >
                {labels.remove}
              </button>
            </li>
          ))}
        </ul>
      )}

      <button type="button" className="btn secondary btn-sm communication-field-add" onClick={addItem}>
        {labels.add} {sectionLabel}
      </button>
    </fieldset>
  );
}
