import React from "react";
import type { ServerDataTableRowSelectionController } from "../../hooks/useServerDataTableRowSelection";
import type { UniversalDataTableColumn } from "./UniversalDataTable";

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
  const checkboxRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = !allPageRowsSelected && somePageRowsSelected;
    }
  }, [allPageRowsSelected, somePageRowsSelected]);

  return (
    <span className="data-table-selection-header">
      <span className="data-table-selection-title">{title}</span>
      <input
        ref={checkboxRef}
        type="checkbox"
        className="data-table-selection-checkbox"
        checked={allPageRowsSelected}
        onChange={(event) => onTogglePage(event.target.checked)}
        aria-label={selectAllAriaLabel}
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
      <input
        type="checkbox"
        className="data-table-selection-checkbox"
        checked={selection.isSelected(row.id)}
        onChange={(event) => selection.toggleRow(row.id, event.target.checked)}
        aria-label={options.rowAriaLabel(row)}
      />
    ),
  };
}
