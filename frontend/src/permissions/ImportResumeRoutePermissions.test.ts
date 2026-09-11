import { describe, expect, it } from "vitest";
import {
  canAccessApplicationPath,
  PERMISSION_IMPORTS_READ,
  PERMISSION_IMPORTS_UPDATE,
} from "./navigationPermissions";

const route = "/data-integration/imports/continue/batch-1";
const granted = (...permissions: string[]) => new Set(permissions);

describe("import resume route permissions", () => {
  it("requires both import read and update permissions", () => {
    expect(canAccessApplicationPath(route, granted())).toBe(false);
    expect(canAccessApplicationPath(route, granted(PERMISSION_IMPORTS_READ))).toBe(false);
    expect(canAccessApplicationPath(route, granted(PERMISSION_IMPORTS_UPDATE))).toBe(false);
    expect(
      canAccessApplicationPath(
        route,
        granted(PERMISSION_IMPORTS_READ, PERMISSION_IMPORTS_UPDATE),
      ),
    ).toBe(true);
  });

  it("keeps query-normalized resume links behind the same combined guard", () => {
    const permissions = granted(PERMISSION_IMPORTS_READ, PERMISSION_IMPORTS_UPDATE);
    expect(canAccessApplicationPath(`${route}?step=mapping`, permissions)).toBe(true);
    expect(canAccessApplicationPath(`${route}?step=mapping`, granted(PERMISSION_IMPORTS_UPDATE))).toBe(
      false,
    );
  });

  it("permits the explicit system/dev bypass", () => {
    expect(canAccessApplicationPath(route, granted(), true)).toBe(true);
  });
});
