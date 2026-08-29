import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/CostCatalogPage.tsx", import.meta.url)),
  "utf8",
);

describe("cost catalog page permission consistency", () => {
  it("loads product category options for read, create or update workflows", () => {
    expect(source).toContain(
      "canProductView || canProductCreate || canProductUpdate",
    );
    expect(source).toContain(
      "canLoadProductCategoryOptions\n          ? listCostProductCategoryOptions()",
    );
    expect(source).toContain(
      "canProductView ? listCostProducts() : Promise.resolve({ items: [] })",
    );
  });

  it("keeps create-only category and product sections reachable without exposing lists", () => {
    expect(source).toContain(
      "canCategoryView || canCategoryCreate || canCategoryUpdate || canCategoryDelete",
    );
    expect(source).toContain(
      "canProductView || canProductCreate || canProductUpdate || canProductDelete",
    );
    expect(source).toContain("{canCategoryView ? (");
    expect(source).toContain("{canProductView ? (");
    expect(source).toContain("canCategoryCreate ? (");
    expect(source).toContain("canProductCreate ? (");
  });

  it("fails closed if write handlers are invoked without the matching permission", () => {
    expect(source).toContain(
      "if ((isUpdate && !canCategoryUpdate) || (!isUpdate && !canCategoryCreate)) return;",
    );
    expect(source).toContain(
      "if ((isUpdate && !canProductUpdate) || (!isUpdate && !canProductCreate)) return;",
    );
    expect(source).toContain("if (!canCategoryDelete) return;");
    expect(source).toContain("if (!canProductDelete) return;");
  });
});
