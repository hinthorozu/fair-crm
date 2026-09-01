import { describe, expect, it } from "vitest";
import { OPERATION_EXECUTE } from "./operationPermissions";
import {
  canAccessApplicationPath,
  PERMISSION_DATA_OPERATIONS_READ,
  PERMISSION_OPERATIONS_CREATE,
  PERMISSION_OPERATIONS_READ,
} from "./navigationPermissions";

const granted = (...permissions: string[]) => new Set(permissions);

describe("data operations route permissions", () => {
  it("requires operation execute plus data-operations read for the duplicate-check wizard", () => {
    expect(
      canAccessApplicationPath("/operations/new/duplicate-check", granted(OPERATION_EXECUTE)),
    ).toBe(false);
    expect(
      canAccessApplicationPath(
        "/operations/new/duplicate-check",
        granted(OPERATION_EXECUTE, PERMISSION_DATA_OPERATIONS_READ),
      ),
    ).toBe(true);
    expect(
      canAccessApplicationPath(
        "/operations/new/duplicate-check",
        granted(PERMISSION_OPERATIONS_CREATE, PERMISSION_DATA_OPERATIONS_READ),
      ),
    ).toBe(false);
  });

  it("preserves create plus data-operations read for the legacy admin surface", () => {
    const createOnly = granted(PERMISSION_OPERATIONS_CREATE);
    expect(canAccessApplicationPath("/admin/data-operations", createOnly)).toBe(false);

    const allowed = granted(PERMISSION_OPERATIONS_CREATE, PERMISSION_DATA_OPERATIONS_READ);
    expect(canAccessApplicationPath("/admin/data-operations", allowed)).toBe(true);
  });

  it("requires operation read plus data-operations read for duplicate-check results", () => {
    const operationsReader = granted(PERMISSION_OPERATIONS_READ);
    expect(
      canAccessApplicationPath("/operations/duplicate-check/runs/run-123", operationsReader),
    ).toBe(false);
    expect(
      canAccessApplicationPath("/admin/data-operations/runs/run-123", operationsReader),
    ).toBe(false);

    const allowed = granted(PERMISSION_OPERATIONS_READ, PERMISSION_DATA_OPERATIONS_READ);
    expect(
      canAccessApplicationPath("/operations/duplicate-check/runs/run-123", allowed),
    ).toBe(true);
    expect(
      canAccessApplicationPath("/admin/data-operations/runs/run-123", allowed),
    ).toBe(true);
  });

  it("does not broaden the general operations routes", () => {
    expect(canAccessApplicationPath("/operations", granted(PERMISSION_DATA_OPERATIONS_READ))).toBe(
      false,
    );
    expect(
      canAccessApplicationPath("/operations/abc", granted(PERMISSION_DATA_OPERATIONS_READ)),
    ).toBe(false);
    expect(
      canAccessApplicationPath("/operations/new/bulk-email", granted(PERMISSION_DATA_OPERATIONS_READ)),
    ).toBe(false);
  });
});
