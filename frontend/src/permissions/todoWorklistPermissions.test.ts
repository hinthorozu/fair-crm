import { describe, expect, it } from "vitest";
import { FAIR_CRM_PERMISSION_CODES } from "./corePermissions";
import { MAIL_SEND_OPERATIONS_PERMISSION_EXECUTE } from "./emailAccountPermissions";
import {
  TODO_PERMISSION_CREATE,
  TODO_PERMISSION_UPDATE,
} from "./todoPermissions";
import { resolveTodoWorklistActionPermissions } from "./todoWorklistPermissions";

describe("todoWorklistPermissions", () => {
  it("requires todo update, not todo create, to record worklist activity", () => {
    expect(
      resolveTodoWorklistActionPermissions(new Set([TODO_PERMISSION_CREATE])).canRecordActivity,
    ).toBe(false);
    expect(
      resolveTodoWorklistActionPermissions(new Set([TODO_PERMISSION_UPDATE])).canRecordActivity,
    ).toBe(true);
  });

  it("requires mail-send execute independently of todo mutation permissions", () => {
    const updateOnly = resolveTodoWorklistActionPermissions(new Set([TODO_PERMISSION_UPDATE]));
    const executeOnly = resolveTodoWorklistActionPermissions(
      new Set([MAIL_SEND_OPERATIONS_PERMISSION_EXECUTE]),
    );

    expect(updateOnly.canSendManualMail).toBe(false);
    expect(executeOnly.canSendManualMail).toBe(true);
    expect(executeOnly.canRecordActivity).toBe(false);
  });

  it("does not introduce a todos execute permission", () => {
    const todoExecutePermission = ["fair_crm", "todos", "execute"].join(".");
    expect(FAIR_CRM_PERMISSION_CODES).not.toContain(todoExecutePermission);
  });
});
