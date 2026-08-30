import { describe, expect, it } from "vitest";
import { CUSTOMER_READ } from "../../permissions/customerPermissions";
import { FAIR_READ } from "../../permissions/fairPermissions";
import {
  canUseTodoCustomerSelector,
  canUseTodoFairSelector,
} from "./TodoForm";

describe("TodoForm entity selector permissions", () => {
  it("requires customers.read for the customer selector", () => {
    expect(canUseTodoCustomerSelector([])).toBe(false);
    expect(canUseTodoCustomerSelector([CUSTOMER_READ])).toBe(true);
  });

  it("requires fairs.read for the fair selector", () => {
    expect(canUseTodoFairSelector([])).toBe(false);
    expect(canUseTodoFairSelector([FAIR_READ])).toBe(true);
  });

  it("keeps the two selector permissions independent", () => {
    expect(canUseTodoCustomerSelector([FAIR_READ])).toBe(false);
    expect(canUseTodoFairSelector([CUSTOMER_READ])).toBe(false);
  });
});
