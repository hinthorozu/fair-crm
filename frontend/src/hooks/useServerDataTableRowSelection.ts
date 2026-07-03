import React from "react";

/** Row selection controller for Universal Server-Side DataTable (ADR-029). */
export interface ServerDataTableRowSelectionController {
  selectedIds: ReadonlySet<string>;
  allPageRowsSelected: boolean;
  somePageRowsSelected: boolean;
  isSelected: (rowId: string) => boolean;
  toggleRow: (rowId: string, checked: boolean) => void;
  togglePage: (checked: boolean) => void;
  clearSelection: () => void;
}

/**
 * Session-scoped row selection for server-side tables.
 * Selection persists across paging, filtering, and sorting via a Set of row IDs.
 * Header "select all" applies to the current page only (`pageRowIds`).
 */
export function useServerDataTableRowSelection(
  pageRowIds: string[],
): ServerDataTableRowSelectionController {
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(() => new Set());

  const allPageRowsSelected =
    pageRowIds.length > 0 && pageRowIds.every((id) => selectedIds.has(id));
  const somePageRowsSelected = pageRowIds.some((id) => selectedIds.has(id));

  const isSelected = React.useCallback((rowId: string) => selectedIds.has(rowId), [selectedIds]);

  const toggleRow = React.useCallback((rowId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(rowId);
      else next.delete(rowId);
      return next;
    });
  }, []);

  const togglePage = React.useCallback(
    (checked: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const id of pageRowIds) {
          if (checked) next.add(id);
          else next.delete(id);
        }
        return next;
      });
    },
    [pageRowIds],
  );

  const clearSelection = React.useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  return {
    selectedIds,
    allPageRowsSelected,
    somePageRowsSelected,
    isSelected,
    toggleRow,
    togglePage,
    clearSelection,
  };
}
