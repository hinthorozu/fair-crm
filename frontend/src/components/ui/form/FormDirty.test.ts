import { afterEach, describe, expect, it } from "vitest";
import {
  clearNavigationDirtySources,
  isNavigationDirty,
  setNavigationDirtySource,
  subscribeNavigationDirty,
} from "./FormDirty";

describe("navigation dirty registry", () => {
  afterEach(() => {
    clearNavigationDirtySources();
  });

  it("tracks dirty sources and notifies subscribers", () => {
    let ticks = 0;
    const unsubscribe = subscribeNavigationDirty(() => {
      ticks += 1;
    });

    expect(isNavigationDirty()).toBe(false);
    setNavigationDirtySource("modal-a", true);
    expect(isNavigationDirty()).toBe(true);
    expect(ticks).toBeGreaterThan(0);

    setNavigationDirtySource("modal-a", false);
    expect(isNavigationDirty()).toBe(false);

    setNavigationDirtySource("page-b", true);
    setNavigationDirtySource("modal-a", true);
    clearNavigationDirtySources();
    expect(isNavigationDirty()).toBe(false);

    unsubscribe();
  });
});
