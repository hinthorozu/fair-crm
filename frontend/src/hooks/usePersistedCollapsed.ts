import React from "react";

function readStoredBoolean(key: string, defaultValue: boolean): boolean {
  if (typeof window === "undefined") return defaultValue;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === "true") return true;
    if (raw === "false") return false;
  } catch {
    // ignore quota / private mode
  }
  return defaultValue;
}

/** Persist sidebar collapsed state in localStorage. */
export function usePersistedCollapsed(storageKey: string, defaultCollapsed = false) {
  const [collapsed, setCollapsedState] = React.useState(() =>
    readStoredBoolean(storageKey, defaultCollapsed),
  );

  const setCollapsed = React.useCallback(
    (value: boolean | ((prev: boolean) => boolean)) => {
      setCollapsedState((prev) => {
        const next = typeof value === "function" ? value(prev) : value;
        try {
          window.localStorage.setItem(storageKey, String(next));
        } catch {
          // ignore
        }
        return next;
      });
    },
    [storageKey],
  );

  const toggleCollapsed = React.useCallback(() => {
    setCollapsed((prev) => !prev);
  }, [setCollapsed]);

  return { collapsed, setCollapsed, toggleCollapsed };
}
