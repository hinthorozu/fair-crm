import React from "react";
import type { CommunicationFormItem } from "../utils/customerCommunicationForm";
import { createCommunicationItem, ensureSinglePrimary } from "../utils/customerCommunicationForm";
import { labels } from "../labels";
import { TextInput } from "./ui/form";

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
              <label className="communication-field-primary">
                <input
                  type="radio"
                  name={`${fieldId}-primary`}
                  checked={item.is_primary}
                  onChange={() => setPrimary(item.id)}
                  aria-label={`${labels.markPrimary} ${sectionLabel}`}
                />
                <span>{labels.primary}</span>
              </label>
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
