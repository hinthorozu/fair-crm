import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/MailTemplatesPage.tsx", import.meta.url)),
  "utf8",
);

describe("Mail Template write permissions", () => {
  it("fails closed before create mutation", () => {
    expect(source).toContain("const handleCreate = async");
    expect(source).toContain("if (!canCreate) return;");
    expect(source).toContain('modal === "create" && canCreate');
  });

  it("fails closed before update mutation", () => {
    expect(source).toContain("const handleUpdate = async");
    expect(source).toContain("if (!canUpdate || !editing) return;");
    expect(source).toContain('modal === "edit" && editing && canUpdate');
  });

  it("fails closed before delete mutation", () => {
    expect(source).toContain("const handleDelete = async");
    expect(source).toContain("if (!canDelete) return;");
    expect(source).toContain("deleteTarget && canDelete");
  });
});
