import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../api/customers.ts", import.meta.url),
  "utf8",
);

describe("customer read client permissions", () => {
  it("fails closed before listing customers without read permission", () => {
    expect(source).toContain("export async function listCustomers");
    expect(source).toContain("throw new ApiError(CUSTOMER_READ_DENIED, 403);");
  });

  it("fails closed before exporting customers without read permission", () => {
    expect(source).toContain("export async function exportCustomers");
    expect(source.match(/throw new ApiError\(CUSTOMER_READ_DENIED, 403\);/g)?.length).toBe(2);
  });

  it("keeps single-customer lookup behind the same permission", () => {
    expect(source).toContain("export function getCustomer");
    expect(source).toContain("return Promise.reject(new ApiError(CUSTOMER_READ_DENIED, 403));");
  });
});
