import { afterEach, describe, expect, it } from "vitest";
import { getCustomer } from "./customers";
import { getFair } from "./fairs";
import { CUSTOMER_READ } from "../permissions/customerPermissions";
import { FAIR_READ } from "../permissions/fairPermissions";
import { replaceGrantedPermissions } from "../permissions/corePermissions";

afterEach(() => {
  replaceGrantedPermissions([]);
});

describe("entity detail lookup permission boundaries", () => {
  it("fails closed before a customer detail lookup without customers.read", async () => {
    replaceGrantedPermissions([]);

    await expect(getCustomer("customer-1")).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining(CUSTOMER_READ),
    });
  });

  it("fails closed before a fair detail lookup without fairs.read", async () => {
    replaceGrantedPermissions([]);

    await expect(getFair("fair-1")).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining(FAIR_READ),
    });
  });
});
