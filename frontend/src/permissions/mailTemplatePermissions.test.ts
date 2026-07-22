import { describe, expect, it } from "vitest";
import {
  canPerformMailTemplateAction,
  hasMailTemplatePermission,
  MAIL_TEMPLATE_PERMISSION_CREATE,
  MAIL_TEMPLATE_PERMISSION_READ,
  MAIL_TEMPLATE_PERMISSION_RENDER,
  MAIL_TEMPLATE_PERMISSION_TEST_SEND,
  MAIL_TEMPLATE_PERMISSION_UPDATE,
} from "./mailTemplatePermissions";

describe("mailTemplatePermissions", () => {
  const readOnly = new Set([MAIL_TEMPLATE_PERMISSION_READ]);

  it("allows actions only when permission is granted", () => {
    expect(canPerformMailTemplateAction(readOnly, "read")).toBe(true);
    expect(canPerformMailTemplateAction(readOnly, "create")).toBe(false);
    expect(canPerformMailTemplateAction(readOnly, "update")).toBe(false);
    expect(canPerformMailTemplateAction(readOnly, "delete")).toBe(false);
    expect(canPerformMailTemplateAction(readOnly, "render")).toBe(false);
  });

  it("grants render only when render permission is present", () => {
    const withRender = new Set([MAIL_TEMPLATE_PERMISSION_READ, MAIL_TEMPLATE_PERMISSION_RENDER]);
    expect(canPerformMailTemplateAction(withRender, "render")).toBe(true);
    expect(hasMailTemplatePermission(withRender, MAIL_TEMPLATE_PERMISSION_RENDER)).toBe(true);
  });

  it("grants create/update when respective permissions are present", () => {
    const adminLike = new Set([
      MAIL_TEMPLATE_PERMISSION_READ,
      MAIL_TEMPLATE_PERMISSION_CREATE,
      MAIL_TEMPLATE_PERMISSION_UPDATE,
      MAIL_TEMPLATE_PERMISSION_TEST_SEND,
    ]);
    expect(canPerformMailTemplateAction(adminLike, "create")).toBe(true);
    expect(canPerformMailTemplateAction(adminLike, "update")).toBe(true);
    expect(canPerformMailTemplateAction(adminLike, "test_send")).toBe(true);
    expect(canPerformMailTemplateAction(adminLike, "render")).toBe(false);
  });
});

describe("canSetDefaultMailTemplate", () => {
  it("allows default action only for active non-default templates with update permission", async () => {
    const { canSetDefaultMailTemplate } = await import("./mailTemplatePermissions");
    const updateGranted = new Set([MAIL_TEMPLATE_PERMISSION_READ, MAIL_TEMPLATE_PERMISSION_UPDATE]);
    expect(
      canSetDefaultMailTemplate({ is_default: false, is_active: true }, updateGranted),
    ).toBe(true);
    expect(
      canSetDefaultMailTemplate({ is_default: true, is_active: true }, updateGranted),
    ).toBe(false);
    expect(
      canSetDefaultMailTemplate({ is_default: false, is_active: false }, updateGranted),
    ).toBe(false);
  });
});
