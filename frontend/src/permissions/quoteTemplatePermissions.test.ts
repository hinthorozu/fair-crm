import { describe, expect, it } from "vitest";
import {
  QUOTE_TEMPLATE_PERMISSION_CREATE,
  QUOTE_TEMPLATE_PERMISSION_READ,
  QUOTE_TEMPLATE_PERMISSION_UPDATE,
} from "./quoteTemplatePermissions";

describe("quote template permissions", () => {
  it("uses distinct permission codes for each action", () => {
    expect(new Set([
      QUOTE_TEMPLATE_PERMISSION_READ,
      QUOTE_TEMPLATE_PERMISSION_CREATE,
      QUOTE_TEMPLATE_PERMISSION_UPDATE,
    ]).size).toBe(3);
  });
});
