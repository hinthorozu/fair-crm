import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandSettingsAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand settings admin page", () => {
  it("is update-only with two singleton sections and no create/delete", () => {
    expect(source).toContain('title="Temel Ayarlar"');
    expect(source).toContain('title="Stand zarfı"');
    expect(source).toContain('title="Runtime"');
    expect(source).toContain("updateFairStandAdminStandDimensions");
    expect(source).toContain("updateFairStandAdminRuntimeSettings");
    expect(source).toContain("getFairStandAdminSettings");
    expect(source).not.toContain("createFairStand");
    expect(source).not.toContain("deleteFairStand");
    expect(source).not.toContain("archiveFairStand");
    expect(source).toContain("FAIR_STAND_SETTINGS_READ");
    expect(source).toContain("FAIR_STAND_SETTINGS_UPDATE");
  });
});
