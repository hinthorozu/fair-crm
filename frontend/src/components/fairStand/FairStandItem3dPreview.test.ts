import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandItem3dPreview.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("FairStandItem3dPreview", () => {
  it("builds envelope from item dimensions only (no scene_* form fields)", () => {
    expect(source).toContain("envelopeFromForm({");
    expect(source).toContain("widthCm: form.width_cm");
    expect(source).toContain("depthCm: form.depth_cm");
    expect(source).toContain("heightCm: form.height_cm");
    expect(source).not.toContain("sceneWidthCm");
    expect(source).not.toContain("scene_width_cm");
    expect(source).not.toContain("sceneDimensions: child.sceneDimensions");
  });

  it("forwards live child dimensions into assembly without sceneDimensions", () => {
    expect(source).toContain("dimensions: child.dimensions");
    expect(source).toContain("buildLiveAssemblyParts");
  });
});
