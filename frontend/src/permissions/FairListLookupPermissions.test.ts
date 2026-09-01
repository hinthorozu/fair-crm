import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../api/fairs.ts", import.meta.url),
  "utf8",
);

describe("fair list lookup permissions", () => {
  it("fails closed before listing fairs without read permission", () => {
    expect(source).toContain("export async function listFairs");
    expect(source).toContain("if (!getGrantedCorePermissions().has(FAIR_READ)) {");
    expect(source).toContain("throw new ApiError(FAIR_READ_DENIED, 403);");
  });

  it("keeps single-fair lookup behind the same permission", () => {
    expect(source).toContain("export function getFair");
    expect(source).toContain("return Promise.reject(new ApiError(FAIR_READ_DENIED, 403));");
  });
});
