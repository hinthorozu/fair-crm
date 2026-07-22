import React from "react";
import { getCustomer, listCustomers } from "../api/customers";
import { customerStatusLabels } from "../labels";
import { todoLabels } from "../labels/todoLabels";
import type { Customer } from "../types/customer";

const PAGE_SIZE = 25;
const DEBOUNCE_MS = 300;

export interface CustomerEntitySelectProps {
  value: string;
  onChange: (customerId: string) => void;
  disabled?: boolean;
  id?: string;
  placeholder?: string;
  allowClear?: boolean;
}

export function CustomerEntitySelect({
  value,
  onChange,
  disabled = false,
  id,
  placeholder,
  allowClear = false,
}: CustomerEntitySelectProps) {
  const [open, setOpen] = React.useState(false);
  const [searchText, setSearchText] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [items, setItems] = React.useState<Customer[]>([]);
  const [page, setPage] = React.useState(1);
  const [hasNext, setHasNext] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [selectedCustomer, setSelectedCustomer] = React.useState<Customer | null>(null);
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
      setSelectedCustomer(null);
      return;
    }
    const inList = items.find((customer) => customer.id === value);
    if (inList) {
      setSelectedCustomer(inList);
      return;
    }
    void getCustomer(value)
      .then((customer) => setSelectedCustomer(customer))
      .catch(() => setSelectedCustomer(null));
  }, [value, items]);

  const fetchPage = React.useCallback(async (pageNum: number, search: string, append: boolean) => {
    const reqId = ++requestIdRef.current;
    if (append) setLoadingMore(true);
    else setLoading(true);

    try {
      const res = await listCustomers({
        page: pageNum,
        pageSize: PAGE_SIZE,
        search: search.trim() || undefined,
        sortBy: "display_name",
        sortOrder: "asc",
      });
      if (reqId !== requestIdRef.current) return;

      setItems((prev) => {
        if (!append) return res.items;
        const seen = new Set(prev.map((customer) => customer.id));
        return [...prev, ...res.items.filter((customer) => !seen.has(customer.id))];
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
  }, []);

  React.useEffect(() => {
    if (!open) return;
    void fetchPage(1, debouncedSearch, false);
  }, [open, debouncedSearch, fetchPage]);

  React.useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current?.contains(event.target as Node)) return;
      setOpen(false);
      setSearchText("");
      setHighlightIndex(-1);
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  const handleScroll = () => {
    const list = listRef.current;
    if (!list || loadingMore || !hasNext || loading) return;
    if (list.scrollTop + list.clientHeight >= list.scrollHeight - 40) {
      void fetchPage(page + 1, debouncedSearch, true);
    }
  };

  const clearSelection = () => {
    onChange("");
    setSelectedCustomer(null);
    setOpen(false);
    setSearchText("");
    setHighlightIndex(-1);
  };

  const selectCustomer = (customer: Customer) => {
    onChange(customer.id);
    setSelectedCustomer(customer);
    setOpen(false);
    setSearchText("");
    setHighlightIndex(-1);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      setSearchText("");
      setHighlightIndex(-1);
      return;
    }

    if (!open && (event.key === "ArrowDown" || event.key === "Enter")) {
      setOpen(true);
      return;
    }

    if (!open) return;

    const optionOffset = allowClear ? 1 : 0;
    const maxIndex = items.length - 1 + optionOffset;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightIndex((prev) => Math.min(prev + 1, maxIndex));
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
        clearSelection();
        return;
      }
      const item = items[highlightIndex - optionOffset];
      if (item) selectCustomer(item);
    }
  };

  const inputValue = open ? searchText : (selectedCustomer?.display_name ?? "");

  return (
    <div className="entity-select" ref={containerRef}>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        aria-controls={id ? `${id}-listbox` : undefined}
        className="entity-select-input"
        value={inputValue}
        placeholder={placeholder ?? todoLabels.fieldCustomerPlaceholder}
        disabled={disabled}
        onChange={(event) => {
          setSearchText(event.target.value);
          setOpen(true);
          setHighlightIndex(-1);
        }}
        onFocus={() => {
          setOpen(true);
          setSearchText("");
        }}
        onKeyDown={handleKeyDown}
      />
      {open && (
        <div
          id={id ? `${id}-listbox` : undefined}
          ref={listRef}
          className="entity-select-dropdown"
          role="listbox"
          onScroll={handleScroll}
        >
          {allowClear ? (
            <button
              type="button"
              role="option"
              aria-selected={!value}
              className={[
                "entity-select-option",
                !value ? "selected" : "",
                highlightIndex === 0 ? "highlighted" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onMouseDown={(event) => event.preventDefault()}
              onClick={clearSelection}
            >
              <span className="entity-select-option-label">{todoLabels.fieldCustomerClear}</span>
            </button>
          ) : null}
          {loading && items.length === 0 ? (
            <div className="entity-select-message">Yükleniyor…</div>
          ) : items.length === 0 ? (
            <div className="entity-select-message">{todoLabels.fieldCustomerNoResults}</div>
          ) : (
            items.map((customer, index) => {
              const optionIndex = index + (allowClear ? 1 : 0);
              return (
                <button
                  key={customer.id}
                  type="button"
                  role="option"
                  aria-selected={customer.id === value}
                  className={[
                    "entity-select-option",
                    customer.id === value ? "selected" : "",
                    optionIndex === highlightIndex ? "highlighted" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectCustomer(customer)}
                >
                  <span className="entity-select-option-label">{customer.display_name}</span>
                  <span className="entity-select-option-meta">
                    {[customer.city, customer.country].filter(Boolean).join(" · ") ||
                      customerStatusLabels[customer.status] ||
                      customer.status}
                  </span>
                </button>
              );
            })
          )}
          {loadingMore && <div className="entity-select-message">Daha fazla yükleniyor…</div>}
        </div>
      )}
    </div>
  );
}
