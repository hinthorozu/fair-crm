/** @vitest-environment jsdom */
import React, {act} from "react";
import {createRoot, type Root} from "react-dom/client";
import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {CustomerEntitySelect} from "./CustomerEntitySelect";

(globalThis as {IS_REACT_ACT_ENVIRONMENT?: boolean}).IS_REACT_ACT_ENVIRONMENT = true;

type Pending = {search: string | undefined; resolve: (names: string[]) => void};

const h = vi.hoisted(() => ({pending: [] as Pending[]}));
vi.mock("../api/customers", () => ({
  listCustomers: (params: {search?: string}) =>
    new Promise((resolve) => {
      h.pending.push({
        search: params.search,
        resolve: (names: string[]) =>
          resolve({
            items: names.map((name) => ({id: `id-${name}`, display_name: name, status: "active"})),
            pagination: {hasNext: false},
          }),
      });
    }),
  getCustomer: vi.fn(async (id: string) => ({id, display_name: id.replace("id-", ""), status: "active"})),
}));

let root: Root;
let container: HTMLDivElement;
let onChange: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.useFakeTimers();
  h.pending = [];
  onChange = vi.fn();
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => {
    root.render(React.createElement(CustomerEntitySelect, {id: "cs", value: "", onChange, allowClear: false}));
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  document.body.innerHTML = "";
  vi.useRealTimers();
});

const input = () => container.querySelector("#cs") as HTMLInputElement;
const options = () => [...document.querySelectorAll("#cs-listbox [role=option]")].map((item) => item.textContent ?? "");
const listText = () => document.querySelector("#cs-listbox")?.textContent ?? "";

function type(value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input(), value);
    input().dispatchEvent(new Event("input", {bubbles: true}));
  });
}

async function resolveLast(names: string[]) {
  await act(async () => {
    h.pending.at(-1)!.resolve(names);
    await Promise.resolve();
  });
}

it("focus alone does not open the list", () => {
  act(() => input().focus());
  expect(input().getAttribute("aria-expanded")).toBe("false");
  expect(document.querySelector("#cs-listbox")).toBeNull();
});

it("hides results of an older search until the typed search answers", async () => {
  act(() => input().click());
  expect(input().getAttribute("aria-expanded")).toBe("true");
  await resolveLast(["(MUGİSS) PİLKASAN", "06 SOGUTMA"]);
  expect(options()).toHaveLength(2);

  type("Beysan");
  // Debounce and request still pending: the unfiltered rows must not be selectable.
  expect(options()).toHaveLength(0);
  expect(listText()).toContain("Aranıyor…");

  await act(async () => {
    vi.advanceTimersByTime(300);
  });
  expect(h.pending.at(-1)!.search).toBe("Beysan");
  expect(options()).toHaveLength(0);

  await resolveLast(["Beysan"]);
  expect(options()).toHaveLength(1);
  expect(options()[0]).toContain("Beysan");

  const option = document.querySelector("#cs-listbox [role=option]") as HTMLButtonElement;
  act(() => option.click());
  expect(onChange).toHaveBeenCalledWith("id-Beysan");
});

it("Enter cannot pick a stale row while a search is pending", async () => {
  act(() => input().click());
  await resolveLast(["(MUGİSS) PİLKASAN"]);
  type("Beysan");
  act(() => {
    input().dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowDown", bubbles: true}));
  });
  act(() => {
    input().dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
  });
  expect(onChange).not.toHaveBeenCalled();
});
