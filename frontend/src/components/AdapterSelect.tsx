import React from "react";
import { listAdapters } from "../api/scraper";
import { FieldError } from "./ui/form";
import { fairLabels } from "../labels/fairLabels";
import type { AdapterListItem } from "../types/scraper";
import { formatAdapterOptionLabel } from "../utils/fairIntegration";

interface AdapterSelectProps {
  id?: string;
  value: string;
  onChange: (adapterKey: string) => void;
  disabled?: boolean;
}

export function AdapterSelect({ id, value, onChange, disabled }: AdapterSelectProps) {
  const [adapters, setAdapters] = React.useState<AdapterListItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [open, setOpen] = React.useState(false);
  const [searchText, setSearchText] = React.useState("");
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void listAdapters()
      .then((response) => {
        if (!cancelled) {
          setAdapters(response.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError(fairLabels.adapterLoadError);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = React.useMemo(
    () => adapters.find((adapter) => adapter.adapter_key === value) ?? null,
    [adapters, value],
  );

  const filtered = React.useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) return adapters;
    return adapters.filter(
      (adapter) =>
        adapter.display_name.toLowerCase().includes(query) ||
        adapter.adapter_key.toLowerCase().includes(query),
    );
  }, [adapters, searchText]);

  const inputValue = open
    ? searchText
    : selected
      ? formatAdapterOptionLabel(selected.display_name, selected.adapter_key)
      : "";

  React.useEffect(() => {
    const onDocumentClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setSearchText("");
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, []);

  const pickAdapter = (adapterKey: string) => {
    onChange(adapterKey);
    setOpen(false);
    setSearchText("");
  };

  return (
    <div className="entity-select" ref={containerRef}>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        className="entity-select-input"
        value={inputValue}
        placeholder={loading ? labelsLoading() : fairLabels.adapterSearchPlaceholder}
        disabled={disabled || loading}
        onChange={(event) => {
          setSearchText(event.target.value);
          setOpen(true);
          if (!event.target.value.trim() && !open) {
            onChange("");
          }
        }}
        onFocus={() => {
          setOpen(true);
          setSearchText("");
        }}
      />
      {loadError ? <FieldError>{loadError}</FieldError> : null}
      {open && !loading && !loadError && (
        <div className="entity-select-dropdown" role="listbox">
          <button
            type="button"
            className={`entity-select-option${value === "" ? " selected" : ""}`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => pickAdapter("")}
          >
            {fairLabels.adapterNone}
          </button>
          {filtered.length === 0 ? (
            <div className="entity-select-message">{fairLabels.adapterNoResults}</div>
          ) : (
            filtered.map((adapter) => (
              <button
                key={adapter.adapter_key}
                type="button"
                className={`entity-select-option${adapter.adapter_key === value ? " selected" : ""}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => pickAdapter(adapter.adapter_key)}
              >
                {formatAdapterOptionLabel(adapter.display_name, adapter.adapter_key)}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function labelsLoading(): string {
  return "Yükleniyor…";
}
