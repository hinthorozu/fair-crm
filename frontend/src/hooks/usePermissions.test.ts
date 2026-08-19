import { describe, expect, it } from "vitest";
import {
  isAnyEffectivePermissionGranted,
  isEffectivePermissionGranted,
} from "./usePermissions";

describe("effective UI permission helpers", () => {
  const granted = ["fair_crm.customers.read", "fair_crm.customers.update"];

  it("keeps independent CRUD permissions independent", () => {
    expect(isEffectivePermissionGranted(granted, "fair_crm.customers.read")).toBe(true);
    expect(isEffectivePermissionGranted(granted, "fair_crm.customers.update")).toBe(true);
    expect(isEffectivePermissionGranted(granted, "fair_crm.customers.create")).toBe(false);
    expect(isEffectivePermissionGranted(granted, "fair_crm.customers.delete")).toBe(false);
    expect(isEffectivePermissionGranted(granted, "fair_crm.customers.execute")).toBe(false);
  });

  it("supports any-of requirements without inventing grants", () => {
    expect(
      isAnyEffectivePermissionGranted(granted, [
        "fair_crm.customers.delete",
        "fair_crm.customers.update",
      ]),
    ).toBe(true);
    expect(
      isAnyEffectivePermissionGranted(granted, [
        "fair_crm.customers.delete",
        "fair_crm.customers.execute",
      ]),
    ).toBe(false);
  });

  it("honors the explicit development bypass", () => {
    expect(isEffectivePermissionGranted([], "fair_crm.customers.delete", true)).toBe(true);
  });
});
