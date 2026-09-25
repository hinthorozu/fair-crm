import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandSettingsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand settings admin page", () => {
  it("uses Fair Stand admin table + modal standards and update-only flow", () => {
    expect(source).toContain("UniversalDataTable");
    expect(source).toContain("SectionHeader");
    expect(source).toContain("FormModal");
    expect(source).toContain("TableRowActions");
    expect(source).toContain("FormSection");
    expect(source).toContain("FormGrid");
    expect(source).toContain('formWidth="standard"');
    expect(source).toContain('formWidth="narrow"');
    expect(source).toContain("adminLabels.fairStandSettingsTitle");
    expect(source).toContain("updateFairStandAdminStandDimensions");
    expect(source).toContain("updateFairStandAdminRuntimeSettings");
    expect(source).toContain("getFairStandAdminSettings");
    expect(source).toContain("fairStandSettingsFieldHeightHint");
    expect(source).toContain("fairStandSettingsFieldDepthHint");
    expect(source).toContain("frameWidthCm");
    expect(source).toContain("panelRailHeightCm");
    expect(source).toContain("fairStandSettingsFieldFrameWidthHint");
    expect(source).toContain("fairStandSettingsFieldPanelRailHeightHint");
    expect(source).not.toContain("fairStandSettingsFieldStripCountHint");
    expect(source).toContain("fairStandSettingsFieldMaxUploadHint");
    expect(source).toContain("fairStandSettingsFieldExportVisibleHint");
    expect(source).toContain("fairStandSettingsFieldSaveAsVisibleHint");
    expect(source).toContain("FAIR_STAND_SETTINGS_READ");
    expect(source).toContain("FAIR_STAND_SETTINGS_UPDATE");
    expect(source).not.toContain("createFairStand");
    expect(source).not.toContain("deleteFairStand");
    expect(source).not.toContain("archiveFairStand");
  });
});
