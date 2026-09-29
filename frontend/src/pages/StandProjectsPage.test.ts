import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

describe("StandProjectsPage", () => {
  it("gates create/edit/delete actions by project permissions", () => {
    const source = readFileSync(join(here, "StandProjectsPage.tsx"), "utf8");
    expect(source).toContain("PERMISSION_STAND_PROJECTS_READ");
    expect(source).toContain("PERMISSION_STAND_PROJECTS_CREATE");
    expect(source).toContain("PERMISSION_STAND_PROJECTS_UPDATE");
    expect(source).toContain("PERMISSION_STAND_PROJECTS_DELETE");
    expect(source).toContain("listFairStandProjects");
    expect(source).toContain("deleteFairStandProject");
    expect(source).toContain("onCreateProject");
    expect(source).toContain("onOpenProject");
    expect(source).toContain("onCreateProject(customerId)");
    expect(source).toContain("onOpenProject(row.id)");
    expect(source).toContain("assignFairStandProjectCustomer");
    expect(source).toContain("CUSTOMER_READ");
    expect(source).toContain("allowClear={false}");
    expect(source).toContain("standProjectsLabels.colCustomer");
    expect(source).toContain("standProjectsLabels.temporaryCustomer");
    expect(source).toContain("standProjectsLabels.actionAssignCustomer");
    expect(source).toContain("standProjectsLabels.assignCustomerTitle");
    expect(source).toContain("standProjectsLabels.assignCustomerConfirm");
    expect(source).toContain("openAssign(row)");
    expect(source).not.toContain("void assignCustomer(");
  });
});
