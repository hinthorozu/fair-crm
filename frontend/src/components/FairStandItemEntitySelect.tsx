import React from "react";
import {
  getFairStandAdminItemRecord,
  listFairStandAdminItemRecords,
  type FairStandAdminItemRecordSummary,
} from "../api/fairStandAdmin";
import { TextInput } from "./ui/form";
import { adminLabels } from "../labels/adminLabels";

const PAGE_SIZE = 25;
const DEBOUNCE_MS = 300;

export interface FairStandItemEntitySelectProps {
  value: string;
  onChange: (itemKey: string) => void;
  disabled?: boolean;
  id?: string;
  placeholder?: string;
  allowClear?: boolean;
  /** Item keys that must not appear in the dropdown (e.g. parent or already added). */
  excludeItemKeys?: string[];
}

function formatItemOptionLabel(itemKey: string, name: string): string {
  const trimmedName = name.trim();
  return trimmedName ? `${itemKey} - ${trimmedName}` : itemKey;
}

export function FairStandItemEntitySelect({
  value,
  onChange,
  disabled = false,
  id,
  placeholder,
  allowClear = true,
  excludeItemKeys = [],
}: FairStandItemEntitySelectProps) {
  const excludedKey = excludeItemKeys.filter(Boolean).slice().sort().join("|");
  const excludedIds = React.useMemo(
    () => new Set(excludedKey ? excludedKey.split("|") : []),
    [excludedKey],
  );

  const [open, setOpen] = React.useState(false);
  const [searchText, setSearchText] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [items, setItems] = React.useState<FairStandAdminItemRecordSummary[]>([]);
  const [page, setPage] = React.useState(1);
  const [hasNext, setHasNext] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [selectedItem, setSelectedItem] = React.useState<{
    itemKey: string;
    name: string;
    type: string;
  } | null>(null);
  const [highlightIndex, setHighlightIndex] = React.useState(-1);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const listRef = React.useRef<HTMLDivElement>(null);
  const requestIdRef = React.useRef(0);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchText), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchText]);

  React.useEffect(() => {
    if (!value) {
      setSelectedItem(null);
      return;
    }
    const inList = items.find((item) => item.itemKey === value);
    if (inList) {
      setSelectedItem({
        itemKey: inList.itemKey,
        name: inList.name,
        type: inList.type,
      });
      return;
    }
    void getFairStandAdminItemRecord(value)
      .then((record) =>
        setSelectedItem({
          itemKey: record.itemKey,
          name: record.name,
          type: record.type,
        }),
      )
      .catch(() => setSelectedItem(null));
  }, [value, items]);

  const fetchPage = React.useCallback(
    async (pageNum: number, search: string, append: boolean) => {
      const reqId = ++requestIdRef.current;
      if (append) setLoadingMore(true);
      else setLoading(true);

      try {
        const res = await listFairStandAdminItemRecords({
          page: pageNum,
          pageSize: PAGE_SIZE,
          search: search.trim() || undefined,
          sortBy: "itemKey",
          sortOrder: "asc",
        });
        if (reqId !== requestIdRef.current) return;

        const visible = res.items.filter((item) => !excludedIds.has(item.itemKey));
        setItems((prev) => {
          if (!append) return visible;
          const seen = new Set(prev.map((item) => item.itemKey));
          return [...prev, ...visible.filter((item) => !seen.has(item.itemKey))];
        });
        setHasNext(res.pagination.hasNext);
        setPage(pageNum);
      } catch {
        if (reqId === requestIdRef.current && !append) setItems([]);
      } finally {
        if (reqId === requestIdRef.current) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [excludedIds],
  );

  React.useEffect(() => {
    if (!open) return;
    void fetchPage(1, debouncedSearch, false);
  }, [open, debouncedSearch, fetchPage]);

  React.useEffect(() => {
    if (value && excludedIds.has(value)) {
      onChange("");
    }
  }, [excludedIds, onChange, value]);

  React.useEffect(() => {
    const onDocumentClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setSearchText("");
        setHighlightIndex(-1);
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, []);

  const optionCount = items.length + (allowClear ? 1 : 0);

  const pickItem = (itemKey: string) => {
    onChange(itemKey);
    setOpen(false);
    setSearchText("");
    setHighlightIndex(-1);
  };

  const inputValue = open
    ? searchText
    : selectedItem
      ? formatItemOptionLabel(selectedItem.itemKey, selectedItem.name)
      : value
        ? value
        : "";

  const onListScroll = () => {
    const list = listRef.current;
    if (!list || loadingMore || !hasNext) return;
    if (list.scrollTop + list.clientHeight >= list.scrollHeight - 24) {
      void fetchPage(page + 1, debouncedSearch, true);
    }
  };

  return (
    <div className="entity-select" ref={containerRef}>
      <TextInput
        id={id ?? "fair-stand-item-entity-select"}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        className="entity-select-input"
        value={inputValue}
        placeholder={placeholder ?? adminLabels.fairStandItemsItemSearchPlaceholder}
        disabled={disabled}
        onChange={(event) => {
          setSearchText(event.target.value);
          setOpen(true);
          setHighlightIndex(-1);
          if (!event.target.value.trim() && value) {
            onChange("");
          }
        }}
        onFocus={() => {
          setOpen(true);
          setSearchText("");
          setHighlightIndex(-1);
        }}
        onKeyDown={(event) => {
          if (!open && (event.key === "ArrowDown" || event.key === "Enter")) {
            setOpen(true);
            return;
          }
          if (!open) return;
          if (event.key === "Escape") {
            setOpen(false);
            setSearchText("");
            setHighlightIndex(-1);
            return;
          }
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setHighlightIndex((prev) => Math.min(prev + 1, optionCount - 1));
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setHighlightIndex((prev) => Math.max(prev - 1, 0));
            return;
          }
          if (event.key === "Enter" && highlightIndex >= 0) {
            event.preventDefault();
            if (allowClear && highlightIndex === 0) {
              pickItem("");
              return;
            }
            const item = items[allowClear ? highlightIndex - 1 : highlightIndex];
            if (item) pickItem(item.itemKey);
          }
        }}
      />
      {open ? (
        <div
          className="entity-select-dropdown"
          role="listbox"
          ref={listRef}
          onScroll={onListScroll}
        >
          {allowClear ? (
            <button
              type="button"
              className={[
                "entity-select-option",
                value === "" ? "selected" : "",
                highlightIndex === 0 ? "highlighted" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => pickItem("")}
            >
              <span className="entity-select-option-label">
                {adminLabels.fairStandItemsItemClearSelection}
              </span>
            </button>
          ) : null}
          {loading ? (
            <div className="entity-select-message">{adminLabels.fairStandItemsItemSearchLoading}</div>
          ) : items.length === 0 ? (
            <div className="entity-select-message">{adminLabels.fairStandItemsItemSearchNoResults}</div>
          ) : (
            items.map((item, index) => {
              const optionIndex = allowClear ? index + 1 : index;
              return (
                <button
                  key={item.itemKey}
                  type="button"
                  className={[
                    "entity-select-option",
                    item.itemKey === value ? "selected" : "",
                    highlightIndex === optionIndex ? "highlighted" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => pickItem(item.itemKey)}
                >
                  <span className="entity-select-option-label">
                    {formatItemOptionLabel(item.itemKey, item.name)}
                  </span>
                  <span className="entity-select-option-meta">{item.type}</span>
                </button>
              );
            })
          )}
          {loadingMore ? (
            <div className="entity-select-message">
              {adminLabels.fairStandItemsItemSearchLoadingMore}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
