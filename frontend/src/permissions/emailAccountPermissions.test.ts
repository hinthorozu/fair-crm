import { describe, expect, it } from "vitest";
import {
  canPerformEmailAccountAction,
  canSetDefaultEmailAccount,
  hasPermission,
  EMAIL_ACCOUNTS_PERMISSION_CREATE,
  EMAIL_ACCOUNTS_PERMISSION_READ,
  EMAIL_ACCOUNTS_PERMISSION_UPDATE,
} from "../permissions/emailAccountPermissions";

describe("emailAccountPermissions", () => {
  const readOnly = new Set([EMAIL_ACCOUNTS_PERMISSION_READ]);

  it("allows actions only when permission is granted", () => {
    expect(canPerformEmailAccountAction(readOnly, "read")).toBe(true);
    expect(canPerformEmailAccountAction(readOnly, "create")).toBe(false);
    expect(hasPermission(readOnly, EMAIL_ACCOUNTS_PERMISSION_UPDATE)).toBe(false);
  });

  it("blocks default action for inactive or already-default accounts", () => {
    const updateGranted = new Set([
      EMAIL_ACCOUNTS_PERMISSION_READ,
      EMAIL_ACCOUNTS_PERMISSION_UPDATE,
    ]);
    expect(
      canSetDefaultEmailAccount({ is_default: false, is_active: true }, updateGranted),
    ).toBe(true);
    expect(
      canSetDefaultEmailAccount({ is_default: true, is_active: true }, updateGranted),
    ).toBe(false);
    expect(
      canSetDefaultEmailAccount({ is_default: false, is_active: false }, updateGranted),
    ).toBe(false);
  });

  it("hides create action without create permission", () => {
    expect(canPerformEmailAccountAction(readOnly, "create")).toBe(false);
    expect(
      canPerformEmailAccountAction(new Set([EMAIL_ACCOUNTS_PERMISSION_CREATE]), "create"),
    ).toBe(true);
  });
});
