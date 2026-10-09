import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./OrganizationsPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

const labels = readFileSync(
  fileURLToPath(new URL("../labels/organizationLabels.ts", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("organizations list", () => {
  it("shows each organization UUID between the name and the actions", () => {
    const nameAt = source.indexOf('key: "name"');
    const idAt = source.indexOf('key: "id"');
    const actionsAt = source.indexOf('key: "actions"');
    expect(nameAt).toBeGreaterThan(-1);
    expect(idAt).toBeGreaterThan(nameAt);
    expect(actionsAt).toBeGreaterThan(idAt);
    expect(source.slice(idAt, actionsAt)).toContain("organizationLabels.organizationId");
    expect(source.slice(idAt, actionsAt)).toContain("organization.id");
    expect(source.slice(idAt, actionsAt)).toContain('className: "col-uuid"');
    expect(labels).toContain('organizationId: "UUID"');
  });
});
