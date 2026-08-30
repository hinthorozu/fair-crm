import { afterEach, describe, expect, it } from "vitest";
import { getCustomer } from "./customers";
import { getFair } from "./fairs";
import { getTodo } from "./todos";
import { getAdapter } from "./scraper";
import { CUSTOMER_READ } from "../permissions/customerPermissions";
import { FAIR_READ } from "../permissions/fairPermissions";
import { TODO_PERMISSION_READ } from "../permissions/todoPermissions";
import { SCRAPER_PERMISSION_READ } from "../permissions/scraperPermissions";
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

  it("fails closed before a todo detail lookup without todos.read", async () => {
    replaceGrantedPermissions([]);

    await expect(getTodo("todo-1")).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining(TODO_PERMISSION_READ),
    });
  });

  it("fails closed before an adapter detail lookup without scraper.read", async () => {
    replaceGrantedPermissions([]);

    await expect(getAdapter("adapter/demo")).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining(SCRAPER_PERMISSION_READ),
    });
  });
});
