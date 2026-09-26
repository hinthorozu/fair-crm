import { describe, expect, it } from "vitest";
import { moveItemInList, nextCatalogIndex } from "./fairStandCategoryAdmin";

describe("fairStandCategoryAdmin helpers", () => {
  it("nextCatalogIndex appends after max", () => {
    expect(nextCatalogIndex([])).toBe("1");
    expect(nextCatalogIndex([{ catalogIndex: 3 }, { catalogIndex: 1 }])).toBe("4");
  });

  it("moveItemInList reorders by 0-based indices", () => {
    expect(moveItemInList(["a", "b", "c", "d"], 3, 0)).toEqual(["d", "a", "b", "c"]);
    expect(moveItemInList(["a", "b", "c"], 0, 2)).toEqual(["b", "c", "a"]);
    expect(moveItemInList(["a", "b"], 0, 0)).toEqual(["a", "b"]);
    expect(moveItemInList(["a", "b"], -1, 1)).toEqual(["a", "b"]);
  });
});
