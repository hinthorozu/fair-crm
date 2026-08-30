import { describe, expect, it } from "vitest";
import { CUSTOMER_READ } from "./customerPermissions";
import { canOpenTodoCustomerAction } from "./todoCustomerActionPermissions";

describe("todo customer action permissions", () => {
  it("requires customers.read before offering customer navigation", () => {
    expect(canOpenTodoCustomerAction([])).toBe(false);
    expect(canOpenTodoCustomerAction([CUSTOMER_READ])).toBe(true);
  });
});
