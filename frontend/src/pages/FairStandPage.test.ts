import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FairStandPage } from "./FairStandPage";

const here = dirname(fileURLToPath(import.meta.url));

describe("FairStandPage standalone host", () => {
  it("renders a full-viewport host with back chrome and without PageShell", () => {
    const html = renderToStaticMarkup(
      React.createElement(FairStandPage, {
        mode: "new",
        onBackToList: () => undefined,
      }),
    );
    expect(html).toContain('data-testid="fair-stand-standalone"');
    expect(html).toContain('data-testid="fair-stand-host"');
    expect(html).toContain("fair-stand-standalone");
    expect(html).toContain("fair-stand-chrome");
    expect(html).not.toContain("page-shell");
    expect(html).not.toContain("sidebar");
    expect(html).not.toContain("app-topbar");
  });

  it("mounts Fair Stand with catalog headers, project id, and capabilities", () => {
    const source = readFileSync(join(here, "FairStandPage.tsx"), "utf8");
    expect(source).toContain("catalogHeaders: buildApiHeaders()");
    expect(source).toContain("initialProjectId");
    expect(source).toContain("capabilities");
    expect(source).toContain('import("@fair-stand/mountFairStand.js")');
    expect(source).not.toContain("FairStandEmbed");
    expect(source).not.toContain("PageShell");
  });
});
