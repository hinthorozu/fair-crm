import { describe, expect, it } from "vitest";
import { categoryWritePayload, nextCatalogIndex } from "./fairStandCategoryAdmin";

describe("Fair Stand category integer admin helpers", () => {
  it("assigns the next unused catalog index", () => {
    expect(nextCatalogIndex([{ catalogIndex: 1 }, { catalogIndex: 6 }])).toBe("7");
  });

  it("writes name, index, and active without a key", () => {
    expect(
      categoryWritePayload({
        catalog_name: "QA",
        catalog_index: "90",
        is_active: true,
      }),
    ).toEqual({
      catalog_name: "QA",
      catalog_index: 90,
      is_active: true,
    });
  });
});
