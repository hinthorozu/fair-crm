import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(new URL("./DatabaseBackupsPage.tsx", import.meta.url), "utf8").replace(
  /\r\n/g,
  "\n",
);

describe("Database backup table selection defaults", () => {
  it("defaults backup and restore scope to full", () => {
    expect(pageSource).toContain('useState<BackupScope>("full")');
    expect(pageSource).toContain("adminLabels.scopeFullDatabase");
    expect(pageSource).toContain("adminLabels.scopeFullBackup");
    expect(pageSource).toContain('scope === "selected_tables"');
  });

  it("renders table checkboxes only in selected mode", () => {
    expect(pageSource).toContain('scope === "selected_tables" ? (');
    expect(pageSource).toContain("adminLabels.scopeDependencyWarning");
    expect(pageSource).toContain("adminLabels.scopeTablesRequired");
  });

  it("does not require tables for the full backup submit path", () => {
    expect(pageSource).toContain('backupScope === "full"');
    expect(pageSource).toContain('backupScope === "selected_tables" ? selectedBackupTables : undefined');
    expect(pageSource).toContain('restoreScope === "selected_tables" ? selectedRestoreTables : undefined');
  });
});
