import React from "react";
import type { CommunicationFormItem } from "../utils/customerCommunicationForm";
import { createCommunicationItem, ensureSinglePrimary } from "../utils/customerCommunicationForm";
import { labels } from "../labels";

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
        <p className="communication-field-empty muted">{labels.communicationEmpty}</p>
      ) : (
        <ul className="communication-field-list">
          {items.map((item) => (
            <li key={item.id} className="communication-field-row">
              <label className="communication-field-primary">
                <input
                  type="radio"
                  name={`${sectionLabel}-primary`}
                  checked={item.is_primary}
                  onChange={() => setPrimary(item.id)}
                  aria-label={`${labels.markPrimary} ${sectionLabel}`}
                />
                <span>{labels.primary}</span>
              </label>
              <input
                type={inputType}
                className="communication-field-input"
                value={item.value}
                placeholder={placeholder}
                onChange={(e) => setValue(item.id, e.target.value)}
              />
              <button
                type="button"
                className="btn secondary communication-field-remove"
                onClick={() => removeItem(item.id)}
              >
                {labels.remove}
              </button>
            </li>
          ))}
        </ul>
      )}

      <button type="button" className="btn secondary communication-field-add" onClick={addItem}>
        {labels.add} {sectionLabel}
      </button>
    </fieldset>
  );
}
