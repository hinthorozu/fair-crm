import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(new URL("./DatabaseBackupsPage.tsx", import.meta.url), "utf8").replace(
  /\r\n/g,
  "\n",
);
const modalSource = readFileSync(
  new URL("../components/admin/RestoreJobDetailModal.tsx", import.meta.url),
  "utf8",
).replace(/\r\n/g, "\n");
const typeSource = readFileSync(new URL("../types/systemBackup.ts", import.meta.url), "utf8").replace(
  /\r\n/g,
  "\n",
);

describe("Database backups dump-then-migrate restore", () => {
  it("treats Core, CRM and Fair Stand as first-class dump targets", () => {
    expect(typeSource).toContain('"kyrox_core" | "fair_crm" | "fair_stand"');
    expect(pageSource).toContain('value: "kyrox_core"');
    expect(pageSource).toContain('value: "fair_crm"');
    expect(pageSource).toContain('value: "fair_stand"');
    expect(pageSource).toContain("adminLabels.restoreWarningKyroxCore");
    expect(pageSource).toContain("adminLabels.restoreWarningFairCrm");
    expect(pageSource).toContain("adminLabels.restoreWarningFairStand");
    expect(pageSource).toContain("adminLabels.restoreUploadWarningKyroxCore");
    expect(pageSource).toContain("adminLabels.restoreUploadWarningFairCrm");
    expect(pageSource).toContain("adminLabels.restoreUploadWarningFairStand");
    expect(pageSource).toContain("adminLabels.restoreUploadHint");
  });

  it("infers each database dump from backup file names", () => {
    expect(pageSource).toContain('if (name.startsWith("kyrox_core_backup_")) return "kyrox_core"');
    expect(pageSource).toContain('if (name.startsWith("fair_stand_backup_")) return "fair_stand"');
    expect(pageSource).toContain('name.startsWith("fair_crm_backup_")');
  });

  it("labels restore jobs for Fair Stand in the detail modal", () => {
    expect(modalSource).toContain('if (key === "fair_stand") return adminLabels.databaseKeyFairStand');
    expect(modalSource).toContain('if (key === "kyrox_core") return adminLabels.databaseKeyKyroxCore');
  });
});
