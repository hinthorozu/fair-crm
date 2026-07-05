import { describe, expect, it } from "vitest";
import {
  canPerformSmtpAction,
  canSetDefaultSmtpAccount,
  hasPermission,
  SMTP_PERMISSION_CREATE,
  SMTP_PERMISSION_READ,
  SMTP_PERMISSION_UPDATE,
} from "../permissions/smtpPermissions";

describe("smtpPermissions", () => {
  const readOnly = new Set([SMTP_PERMISSION_READ]);

  it("allows actions only when permission is granted", () => {
    expect(canPerformSmtpAction(readOnly, "read")).toBe(true);
    expect(canPerformSmtpAction(readOnly, "create")).toBe(false);
    expect(hasPermission(readOnly, SMTP_PERMISSION_UPDATE)).toBe(false);
  });

  it("blocks default action for inactive or already-default accounts", () => {
    const updateGranted = new Set([SMTP_PERMISSION_READ, SMTP_PERMISSION_UPDATE]);
    expect(
      canSetDefaultSmtpAccount({ is_default: false, is_active: true }, updateGranted),
    ).toBe(true);
    expect(
      canSetDefaultSmtpAccount({ is_default: true, is_active: true }, updateGranted),
    ).toBe(false);
    expect(
      canSetDefaultSmtpAccount({ is_default: false, is_active: false }, updateGranted),
    ).toBe(false);
  });

  it("hides create action without create permission", () => {
    expect(canPerformSmtpAction(readOnly, "create")).toBe(false);
    expect(canPerformSmtpAction(new Set([SMTP_PERMISSION_CREATE]), "create")).toBe(true);
  });
});
