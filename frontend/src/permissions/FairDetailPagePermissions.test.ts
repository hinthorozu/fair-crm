import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/FairDetailPage.tsx", import.meta.url)),
  "utf8",
);

const participationPermissionSource = readFileSync(
  fileURLToPath(new URL("./participationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Fair detail permission-controlled surfaces", () => {
  it("uses the canonical Core participation CRUD permission codes", () => {
    expect(participationPermissionSource).toContain(
      'PARTICIPATION_READ = "fair_crm.participations.read"',
    );
    expect(participationPermissionSource).toContain(
      'PARTICIPATION_CREATE = "fair_crm.participations.create"',
    );
    expect(participationPermissionSource).toContain(
      'PARTICIPATION_UPDATE = "fair_crm.participations.update"',
    );
    expect(participationPermissionSource).toContain(
      'PARTICIPATION_DELETE = "fair_crm.participations.delete"',
    );
  });

  it("does not load or expose the participants tab without participation read permission", () => {
    expect(source).toContain("const canReadParticipants = can(PARTICIPATION_READ)");
    expect(source).toContain(
      'enabled: canReadParticipants && activeTab === "participants" && Boolean(fair)',
    );
    expect(source).toContain('if (!canReadParticipants && activeTab === "participants")');
    expect(source).toContain("...(canReadParticipants");
    expect(source).toContain("{canReadParticipants && (");
    expect(source).toContain("if (!canReadParticipants) {");
  });

  it("gates fair mutations and participant mutations independently", () => {
    expect(source).toContain("const canUpdateFair = can(FAIR_UPDATE)");
    expect(source).toContain("const canDeleteFair = can(FAIR_DELETE)");
    expect(source).toContain("const canCreateParticipation = can(PARTICIPATION_CREATE)");
    expect(source).toContain("const canUpdateParticipation = can(PARTICIPATION_UPDATE)");
    expect(source).toContain("const canDeleteParticipation = can(PARTICIPATION_DELETE)");
    expect(source).toContain("if (canUpdateFair) {");
    expect(source).toContain("if (canCreateParticipation) {");
    expect(source).toContain("if (canUpdateParticipation) {");
    expect(source).toContain("if (canDeleteFair) {");
    expect(source).toContain("onCreate={canCreateParticipation ? openCreateParticipant : undefined}");
    expect(source).toContain("onDelete={canDeleteParticipation ? (item) => setConfirmDelete(item) : undefined}");
  });

  it("gates import and scraper-adjacent behavior by their existing Core permissions", () => {
    expect(source).toContain("const canImportParticipants = can(PERMISSION_IMPORTS_CREATE)");
    expect(source).toContain("const canReadScraper = can(PERMISSION_SCRAPER_READ)");
    expect(source).toContain("if (canImportParticipants) {");
    expect(source).toContain("if (!canReadScraper) {");
  });

  it("fails closed if effective permissions change while dialogs are open", () => {
    expect(source).toContain('modal === "edit-fair" && canUpdateFair');
    expect(source).toContain('modal === "create" && canCreateParticipation');
    expect(source).toContain('modal === "edit" && editing && canUpdateParticipation');
    expect(source).toContain('open={canUpdateParticipation && modal === "move-customers"}');
    expect(source).toContain("confirmDelete && canDeleteParticipation");
    expect(source).toContain("confirmArchive && canDeleteFair");
  });
});
