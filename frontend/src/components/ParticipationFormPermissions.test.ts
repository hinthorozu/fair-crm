import { describe, expect, it } from "vitest";
import {
  canUseParticipationEntitySelector,
  getParticipationSelectorReadPermission,
} from "./ParticipationForm";
import { CUSTOMER_READ } from "../permissions/customerPermissions";
import { FAIR_READ } from "../permissions/fairPermissions";

describe("participation form entity selector permissions", () => {
  it("requires fairs.read when customer-context create must select a fair", () => {
    expect(getParticipationSelectorReadPermission("customer")).toBe(FAIR_READ);
    expect(canUseParticipationEntitySelector(new Set(), "customer")).toBe(false);
    expect(canUseParticipationEntitySelector(new Set([FAIR_READ]), "customer")).toBe(true);
  });

  it("requires customers.read when fair-context create must select a customer", () => {
    expect(getParticipationSelectorReadPermission("fair")).toBe(CUSTOMER_READ);
    expect(canUseParticipationEntitySelector(new Set(), "fair")).toBe(false);
    expect(canUseParticipationEntitySelector(new Set([CUSTOMER_READ]), "fair")).toBe(true);
  });

  it("does not require lookup read permission when the related entity is locked during edit", () => {
    expect(getParticipationSelectorReadPermission("customer", true, false)).toBeNull();
    expect(getParticipationSelectorReadPermission("fair", false, true)).toBeNull();
    expect(canUseParticipationEntitySelector(new Set(), "customer", true, false)).toBe(true);
    expect(canUseParticipationEntitySelector(new Set(), "fair", false, true)).toBe(true);
  });
});
