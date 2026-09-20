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

describe("Database backups Fair Stand option", () => {
  it("treats fair_stand as a first-class database key", () => {
    expect(typeSource).toContain('"kyrox_core" | "fair_crm" | "fair_stand"');
    expect(pageSource).toContain('value: "fair_stand"');
    expect(pageSource).toContain("adminLabels.databaseKeyFairStand");
    expect(pageSource).toContain("adminLabels.restoreWarningFairStand");
    expect(pageSource).toContain("adminLabels.restoreUploadWarningFairStand");
  });

  it("infers Fair Stand dumps from backup file names", () => {
    expect(pageSource).toContain('if (name.startsWith("fair_stand_backup_")) return "fair_stand"');
  });

  it("labels Fair Stand restore jobs in the detail modal", () => {
    expect(modalSource).toContain('if (key === "fair_stand") return adminLabels.databaseKeyFairStand');
  });
});
