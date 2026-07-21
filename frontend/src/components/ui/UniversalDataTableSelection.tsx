import React from "react";
import type { ServerDataTableRowSelectionController } from "../../hooks/useServerDataTableRowSelection";
import type { UniversalDataTableColumn } from "./UniversalDataTable";
import { CheckboxField } from "./form";

interface SelectionColumnHeaderProps {
  title: string;
  selectAllAriaLabel: string;
  allPageRowsSelected: boolean;
  somePageRowsSelected: boolean;
  onTogglePage: (checked: boolean) => void;
}

function SelectionColumnHeader({
  title,
  selectAllAriaLabel,
  allPageRowsSelected,
  somePageRowsSelected,
  onTogglePage,
}: SelectionColumnHeaderProps) {
  return (
    <span className="data-table-selection-header">
      <span className="data-table-selection-title">{title}</span>
      <CheckboxField
        id="data-table-select-all-page"
        label={selectAllAriaLabel}
        checked={allPageRowsSelected}
        indeterminate={!allPageRowsSelected && somePageRowsSelected}
        onChange={onTogglePage}
        hideLabel
        className="data-table-selection-checkbox-wrap"
        inputClassName="data-table-selection-checkbox"
      />
    </span>
  );
}

export function buildUniversalDataTableSelectionColumn<T extends { id: string }>(
  selection: ServerDataTableRowSelectionController,
  options: {
    title: string;
    selectAllAriaLabel: string;
    rowAriaLabel: (row: T) => string;
  },
): UniversalDataTableColumn<T> {
  return {
    key: "selection",
    title: (
      <SelectionColumnHeader
        title={options.title}
        selectAllAriaLabel={options.selectAllAriaLabel}
        allPageRowsSelected={selection.allPageRowsSelected}
        somePageRowsSelected={selection.somePageRowsSelected}
        onTogglePage={selection.togglePage}
      />
    ),
    dataLabel: options.title,
    sortable: false,
    priority: "primary",
    className: "data-table-selection-col",
    render: (row) => (
      <CheckboxField
        id={`data-table-row-select-${row.id}`}
        label={options.rowAriaLabel(row)}
        checked={selection.isSelected(row.id)}
        onChange={(checked) => selection.toggleRow(row.id, checked)}
        hideLabel
        className="data-table-selection-checkbox-wrap"
        inputClassName="data-table-selection-checkbox"
      />
    ),
  };
}
