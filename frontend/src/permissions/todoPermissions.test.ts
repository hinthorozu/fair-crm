import { describe, expect, it } from "vitest";
import {
  canPerformTodoAction,
  TODO_PERMISSION_ARCHIVE,
  TODO_PERMISSION_CREATE,
  TODO_PERMISSION_DELETE,
  TODO_PERMISSION_READ,
  TODO_PERMISSION_UPDATE,
} from "../permissions/todoPermissions";

describe("todoPermissions", () => {
  const readOnly = new Set([TODO_PERMISSION_READ]);

  it("allows actions only when permission is granted", () => {
    expect(canPerformTodoAction(readOnly, "read")).toBe(true);
    expect(canPerformTodoAction(readOnly, "create")).toBe(false);
    expect(canPerformTodoAction(readOnly, "update")).toBe(false);
    expect(canPerformTodoAction(readOnly, "archive")).toBe(false);
    expect(canPerformTodoAction(readOnly, "delete")).toBe(false);
  });

  it("grants create/update/archive/delete when respective permissions are present", () => {
    expect(
      canPerformTodoAction(
        new Set([TODO_PERMISSION_READ, TODO_PERMISSION_CREATE]),
        "create",
      ),
    ).toBe(true);
    expect(
      canPerformTodoAction(
        new Set([TODO_PERMISSION_READ, TODO_PERMISSION_UPDATE]),
        "update",
      ),
    ).toBe(true);
    expect(
      canPerformTodoAction(
        new Set([TODO_PERMISSION_READ, TODO_PERMISSION_ARCHIVE]),
        "archive",
      ),
    ).toBe(true);
    expect(
      canPerformTodoAction(
        new Set([TODO_PERMISSION_READ, TODO_PERMISSION_DELETE]),
        "delete",
      ),
    ).toBe(true);
  });
});
