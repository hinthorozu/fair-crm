/**
 * @vitest-environment jsdom
 */
import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { StandardListResponse } from "../types/listTable";
import { useServerDataTable, type ServerTableFetchParams } from "./useServerDataTable";

type Row = { id: string; name: string };

function listResponse(items: Row[]): StandardListResponse<Row> {
  return {
    items,
    pagination: {
      page: 1,
      pageSize: 25,
      totalItems: items.length,
      totalPages: items.length === 0 ? 0 : 1,
      hasNext: false,
      hasPrevious: false,
    },
    sorting: { field: "name", direction: "asc" },
    filters: {},
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

type TableApi = ReturnType<typeof useServerDataTable<Row>>;

function HookHost({
  fetchFn,
  onReady,
}: {
  fetchFn: (params: ServerTableFetchParams) => Promise<StandardListResponse<Row>>;
  onReady: (api: TableApi) => void;
}) {
  const table = useServerDataTable<Row>({
    fetchFn,
    urlSync: false,
    debounceMs: 0,
    enabled: true,
  });
  React.useEffect(() => {
    onReady(table);
  });
  return null;
}

describe("useServerDataTable silent/initial race", () => {
  let container: HTMLDivElement;
  let root: Root;
  let latest: TableApi | null;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    latest = null;
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("clears loading when silent refresh wins over an in-flight initial load", async () => {
    const initial = createDeferred<StandardListResponse<Row>>();
    const silent = createDeferred<StandardListResponse<Row>>();
    let call = 0;
    const fetchFn = vi.fn(async () => {
      call += 1;
      return call === 1 ? initial.promise : silent.promise;
    });

    await act(async () => {
      root.render(
        React.createElement(HookHost, {
          fetchFn,
          onReady: (api: TableApi) => {
            latest = api;
          },
        }),
      );
    });

    expect(latest).not.toBeNull();
    expect(latest!.loading).toBe(true);
    expect(fetchFn).toHaveBeenCalledTimes(1);

    await act(async () => {
      void latest!.refresh({ silent: true });
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
    expect(latest!.loading).toBe(true);

    await act(async () => {
      silent.resolve(listResponse([{ id: "s1", name: "silent-winner" }]));
      await silent.promise;
    });

    expect(latest!.loading).toBe(false);
    expect(latest!.isRefreshing).toBe(false);
    expect(latest!.items).toEqual([{ id: "s1", name: "silent-winner" }]);

    await act(async () => {
      initial.resolve(listResponse([{ id: "i1", name: "stale-initial" }]));
      await initial.promise;
    });

    // Stale initial must not overwrite the silent winner.
    expect(latest!.items).toEqual([{ id: "s1", name: "silent-winner" }]);
    expect(latest!.loading).toBe(false);
  });

  it("keeps silent refresh from flipping loading when data is already present", async () => {
    const first = createDeferred<StandardListResponse<Row>>();
    const second = createDeferred<StandardListResponse<Row>>();
    let call = 0;
    const fetchFn = vi.fn(async () => {
      call += 1;
      return call === 1 ? first.promise : second.promise;
    });

    await act(async () => {
      root.render(
        React.createElement(HookHost, {
          fetchFn,
          onReady: (api: TableApi) => {
            latest = api;
          },
        }),
      );
    });

    await act(async () => {
      first.resolve(listResponse([{ id: "a", name: "alpha" }]));
      await first.promise;
    });
    expect(latest!.loading).toBe(false);
    expect(latest!.items).toEqual([{ id: "a", name: "alpha" }]);

    await act(async () => {
      void latest!.refresh({ silent: true });
    });
    // Silent must not re-enter skeleton loading.
    expect(latest!.loading).toBe(false);
    expect(latest!.isRefreshing).toBe(true);
    expect(latest!.items).toEqual([{ id: "a", name: "alpha" }]);

    await act(async () => {
      second.resolve(listResponse([{ id: "b", name: "beta" }]));
      await second.promise;
    });
    expect(latest!.loading).toBe(false);
    expect(latest!.isRefreshing).toBe(false);
    expect(latest!.items).toEqual([{ id: "b", name: "beta" }]);
  });

  it("does not let a stale silent response overwrite a newer normal load", async () => {
    const silent = createDeferred<StandardListResponse<Row>>();
    const newer = createDeferred<StandardListResponse<Row>>();
    let call = 0;
    const fetchFn = vi.fn(async () => {
      call += 1;
      if (call === 1) {
        return listResponse([{ id: "boot", name: "boot" }]);
      }
      return call === 2 ? silent.promise : newer.promise;
    });

    await act(async () => {
      root.render(
        React.createElement(HookHost, {
          fetchFn,
          onReady: (api: TableApi) => {
            latest = api;
          },
        }),
      );
    });
    // Let boot load settle.
    await act(async () => {
      await Promise.resolve();
    });
    expect(latest!.items[0]?.id).toBe("boot");

    await act(async () => {
      void latest!.refresh({ silent: true });
    });
    await act(async () => {
      void latest!.refresh();
    });

    await act(async () => {
      newer.resolve(listResponse([{ id: "new", name: "newest" }]));
      await newer.promise;
    });
    expect(latest!.items).toEqual([{ id: "new", name: "newest" }]);
    expect(latest!.loading).toBe(false);

    await act(async () => {
      silent.resolve(listResponse([{ id: "old", name: "stale-silent" }]));
      await silent.promise;
    });
    expect(latest!.items).toEqual([{ id: "new", name: "newest" }]);
    expect(latest!.loading).toBe(false);
  });
});
