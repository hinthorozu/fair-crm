import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/OperationCapabilitiesAdminPage.tsx", import.meta.url),
  "utf8",
);

describe("OperationCapabilitiesAdminPage permissions", () => {
  it("fails closed before opening and saving capability edits", () => {
    expect(source).toContain("if (!canUpdate) return;");
    expect(source).toContain("if (!canUpdate || !editing) return;");
    expect(source).toContain("editing && canUpdate");
  });

  it("hides edit affordances without update permission", () => {
    expect(source).toContain("...(canUpdate");
    expect(source).toContain("canUpdate ? (");
  });
});
