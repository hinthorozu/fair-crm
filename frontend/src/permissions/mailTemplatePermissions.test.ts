import { describe, expect, it } from "vitest";
import {
  canPerformMailTemplateAction,
  hasMailTemplatePermission,
  MAIL_TEMPLATE_PERMISSION_CREATE,
  MAIL_TEMPLATE_PERMISSION_EXECUTE,
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
    expect(canPerformMailTemplateAction(readOnly, "test_send")).toBe(false);
  });

  it("uses one execute permission for render and test-send actions", () => {
    const withExecute = new Set([MAIL_TEMPLATE_PERMISSION_READ, MAIL_TEMPLATE_PERMISSION_EXECUTE]);
    expect(MAIL_TEMPLATE_PERMISSION_RENDER).toBe(MAIL_TEMPLATE_PERMISSION_EXECUTE);
    expect(MAIL_TEMPLATE_PERMISSION_TEST_SEND).toBe(MAIL_TEMPLATE_PERMISSION_EXECUTE);
    expect(canPerformMailTemplateAction(withExecute, "render")).toBe(true);
    expect(canPerformMailTemplateAction(withExecute, "test_send")).toBe(true);
    expect(hasMailTemplatePermission(withExecute, MAIL_TEMPLATE_PERMISSION_EXECUTE)).toBe(true);
  });

  it("keeps create/update separate from execute", () => {
    const editor = new Set([
      MAIL_TEMPLATE_PERMISSION_READ,
      MAIL_TEMPLATE_PERMISSION_CREATE,
      MAIL_TEMPLATE_PERMISSION_UPDATE,
    ]);
    expect(canPerformMailTemplateAction(editor, "create")).toBe(true);
    expect(canPerformMailTemplateAction(editor, "update")).toBe(true);
    expect(canPerformMailTemplateAction(editor, "test_send")).toBe(false);
    expect(canPerformMailTemplateAction(editor, "render")).toBe(false);
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
